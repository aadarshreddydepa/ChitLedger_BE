from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# ---------- User Manager ----------
class UserManager(BaseUserManager):
    def create_user(self, phone_number, name, password=None, **extra_fields):
        """Create and save a regular user with phone number + password"""
        if not phone_number:
            raise ValueError("Users must have a phone number")
        user = self.model(phone_number=phone_number, name=name, **extra_fields)
        user.set_password(password)  # password is hashed here
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, name, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(phone_number, name, password, **extra_fields)


# ---------- User ----------
class User(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    phone_number = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"   # login with phone number
    REQUIRED_FIELDS = ["name"]        # when creating superuser

    def __str__(self):
        return f"{self.name} ({self.phone_number})"


# ---------- Chit ----------
class Chit(models.Model):
    chit_id = models.AutoField(primary_key=True)
    organizer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organized_chits"
    )
    title = models.CharField(max_length=100)
    total_slots = models.PositiveIntegerField()
    monthly_contribution = models.DecimalField(max_digits=12, decimal_places=2)
    start_date = models.DateField()
    duration_months = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.chit_id})"


# ---------- Membership ----------
class Membership(models.Model):
    membership_id = models.AutoField(primary_key=True)
    chit = models.ForeignKey(
        Chit, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="memberships"
    )
    slot_count = models.PositiveIntegerField(default=1)  # can take multiple slots
    is_organizer = models.BooleanField(default=False)
    joined_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("chit", "user")  # prevent duplicate rows

    def __str__(self):
        return f"{self.user.name} in {self.chit.title} ({self.slot_count} slots)"


# ---------- Payment ----------
class Payment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("late", "Late"),
    )
    payment_id = models.AutoField(primary_key=True)
    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="payments"
    )
    month_number = models.PositiveIntegerField()  # 1, 2, 3 ... duration
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"Payment {self.payment_id} - {self.status}"
