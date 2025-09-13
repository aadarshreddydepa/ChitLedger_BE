from django.contrib import admin

# Register your models here.
from .models import User, Chit, Membership, Payment

admin.site.register(User)
admin.site.register(Chit)
admin.site.register(Membership)
admin.site.register(Payment)
