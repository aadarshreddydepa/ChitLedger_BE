from rest_framework import serializers
from .models import Chit, ChitSchedule, ExternalMember, Membership, Payment, User


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ["user_id", "phone_number", "name", "password"]
        read_only_fields = ["user_id"] #check what is ready only later 

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(**validated_data, password=password)
        user.is_verified = True   # mark as verified (after OTP)
        user.save()
        return user


class UserSigninSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

class ExternalMemberCreateSerializer(serializers.ModelSerializer):
    """For adding external members during chit creation"""
    class Meta:
        model = ExternalMember
        fields = ['phone_number', 'name', 'slot_count', 'is_organizer']


class ChitCreateSerializer(serializers.ModelSerializer):
    """For creating chit with external members"""
    external_members_data = ExternalMemberCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Chit
        fields = ['title', 'total_slots', 'total_amount', 'lift_amount',
                  'start_date', 'duration_months', 'external_members_data']
    
    def validate(self, data):
        # Validate that external members don't exceed total slots
        external_members = data.get('external_members_data', [])
        total_external_slots = sum(member.get('slot_count', 1) for member in external_members)
        
        if total_external_slots > data['total_slots']:
            raise serializers.ValidationError(
                f"Total slots ({total_external_slots}) exceed available slots ({data['total_slots']})"
            )
        
        return data
    
    def create(self, validated_data):
        external_members_data = validated_data.pop('external_members_data', [])
        organizer = self.context['request'].user
        
        # Create chit
        chit = Chit.objects.create(organizer=organizer, **validated_data)
        
        # Add external members
        for member_data in external_members_data:
            ExternalMember.objects.create(chit=chit, **member_data)
        
        # Generate monthly schedules with default no_lift_amount
        # Formula: no_lift_amount = (total_amount - lift_amount) / (total_slots - 1)
        default_no_lift = (chit.total_amount - chit.lift_amount) / (chit.total_slots - 1) if chit.total_slots > 1 else 0
        
        for month in range(1, chit.duration_months + 1):
            ChitSchedule.objects.create(
                chit=chit,
                month_number=month,
                lift_amount=chit.lift_amount,
                no_lift_amount=default_no_lift
            )
        
        return chit
    
# ---------- Chit Serializers ----------
class ChitListSerializer(serializers.ModelSerializer):
    """Simple list view of chits"""
    organizer_name = serializers.CharField(source='organizer.name', read_only=True)
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chit
        fields = ['chit_id', 'title', 'total_slots', 'total_amount', 'lift_amount',
                  'start_date', 'duration_months', 'organizer_name', 'member_count', 'created_at']
    
    def get_member_count(self, obj):
        verified = obj.memberships.count()
        external = obj.external_members.count()
        return verified + external
    
# ---------- Membership Serializers ----------
class MembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_phone = serializers.CharField(source='user.phone_number', read_only=True)
    
    class Meta:
        model = Membership
        fields = ['membership_id', 'chit', 'user', 'user_name', 'user_phone', 
                  'slot_count', 'is_organizer', 'joined_date']
        read_only_fields = ['membership_id', 'joined_date']

# ---------- External Member Serializers ----------
class ExternalMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalMember
        fields = ['member_id', 'chit', 'phone_number', 'name', 'slot_count', 'is_organizer', 'joined_date']
        read_only_fields = ['member_id', 'joined_date']




# ---------- Payment Serializers ----------
class PaymentSerializer(serializers.ModelSerializer):
    """Complete payment details for read operations"""
    member_name = serializers.SerializerMethodField()
    member_phone = serializers.SerializerMethodField()
    member_type = serializers.SerializerMethodField()
    chit_title = serializers.CharField(source='chit_schedule.chit.title', read_only=True)
    
    class Meta:
        model = Payment
        fields = ['payment_id', 'membership', 'external_member', 'chit_schedule',
                  'month_number', 'amount_paid', 'payment_date', 'status',
                  'member_name', 'member_phone', 'member_type', 'chit_title']
        read_only_fields = ['payment_id', 'payment_date']
    
    def get_member_name(self, obj):
        if obj.membership:
            return obj.membership.user.name
        elif obj.external_member:
            return obj.external_member.name
        return None
    
    def get_member_phone(self, obj):
        if obj.membership:
            return obj.membership.user.phone_number
        elif obj.external_member:
            return obj.external_member.phone_number
        return None
    
    def get_member_type(self, obj):
        if obj.membership:
            return 'verified'
        elif obj.external_member:
            return 'external'
        return None



class PaymentCreateSerializer(serializers.ModelSerializer):
    """For recording payments - simplified for create operations"""
    membership = serializers.PrimaryKeyRelatedField(
        queryset=Membership.objects.all(),
        required=False,
        allow_null=True
    )
    external_member = serializers.PrimaryKeyRelatedField(
        queryset=ExternalMember.objects.all(),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Payment
        fields = ['membership', 'external_member', 'chit_schedule', 
                  'month_number', 'amount_paid', 'status']
    
    def validate(self, data):
        # Ensure only one member type is provided
        membership = data.get('membership')
        external_member = data.get('external_member')
        
        if membership and external_member:
            raise serializers.ValidationError(
                "Cannot assign payment to both verified and external member"
            )
        if not membership and not external_member:
            raise serializers.ValidationError(
                "Must assign payment to either verified or external member"
            )
        return data




# ---------- Chit Schedule Serializers ----------
class ChitScheduleSerializer(serializers.ModelSerializer):
    lifted_by_name = serializers.SerializerMethodField()
    lifted_by_phone = serializers.SerializerMethodField()
    lifted_by_type = serializers.SerializerMethodField()
    
    class Meta:
        model = ChitSchedule
        fields = ['id', 'chit', 'month_number', 'lift_amount', 'no_lift_amount',
                  'lifted_by_membership', 'lifted_by_external', 
                  'lifted_by_name', 'lifted_by_phone', 'lifted_by_type']
    
    def get_lifted_by_name(self, obj):
        if obj.lifted_by_membership:
            return obj.lifted_by_membership.user.name
        elif obj.lifted_by_external:
            return obj.lifted_by_external.name
        return None
    
    def get_lifted_by_phone(self, obj):
        if obj.lifted_by_membership:
            return obj.lifted_by_membership.user.phone_number
        elif obj.lifted_by_external:
            return obj.lifted_by_external.phone_number
        return None
    
    def get_lifted_by_type(self, obj):
        if obj.lifted_by_membership:
            return 'verified'
        elif obj.lifted_by_external:
            return 'external'
        return None


class ChitScheduleUpdateSerializer(serializers.ModelSerializer):
    """For updating monthly lift assignment and amounts"""
    class Meta:
        model = ChitSchedule
        fields = ['no_lift_amount', 'lifted_by_membership', 'lifted_by_external']
    
    def validate(self, data):
        # Ensure only one lifter is assigned
        if data.get('lifted_by_membership') and data.get('lifted_by_external'):
            raise serializers.ValidationError(
                "Cannot assign both verified member and external member as lifter"
            )
        return data
    
class ChitDetailSerializer(serializers.ModelSerializer):
    """Detailed view with members and schedules"""
    organizer_name = serializers.CharField(source='organizer.name', read_only=True)
    organizer_phone = serializers.CharField(source='organizer.phone_number', read_only=True)
    memberships = MembershipSerializer(many=True, read_only=True)
    external_members = ExternalMemberSerializer(many=True, read_only=True)
    schedules = ChitScheduleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Chit
        fields = ['chit_id', 'organizer', 'organizer_name', 'organizer_phone',
                  'title', 'total_slots', 'total_amount', 'lift_amount',
                  'start_date', 'duration_months', 'created_at',
                  'memberships', 'external_members', 'schedules']

# Dashboard 



class PaymentSummarySerializer(serializers.Serializer):
    """Summary of payments for a month"""
    month_number = serializers.IntegerField()
    lift_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    no_lift_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expected = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid_count = serializers.IntegerField()
    pending_count = serializers.IntegerField()
    late_count = serializers.IntegerField()
    lifter = serializers.DictField(allow_null=True)


class MemberInfoSerializer(serializers.Serializer):
    """Unified member info (verified or external)"""
    id = serializers.IntegerField()
    type = serializers.CharField()
    name = serializers.CharField()
    phone_number = serializers.CharField()
    slot_count = serializers.IntegerField()
    is_organizer = serializers.BooleanField()
    joined_date = serializers.DateTimeField()


class ChitDashboardSerializer(serializers.Serializer):
    """Complete chit dashboard data"""
    chit_id = serializers.IntegerField()
    title = serializers.CharField()
    organizer = serializers.DictField()
    total_slots = serializers.IntegerField()
    used_slots = serializers.IntegerField()
    available_slots = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    lift_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    start_date = serializers.DateField()
    duration_months = serializers.IntegerField()
    current_month = serializers.IntegerField(allow_null=True)
    current_month_summary = PaymentSummarySerializer(allow_null=True)
    members = MemberInfoSerializer(many=True)
    schedules = serializers.ListField()


class OrganizerChitSummarySerializer(serializers.Serializer):
    """Summary of a single chit for organizer dashboard"""
    chit_id = serializers.IntegerField()
    title = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    start_date = serializers.DateField()
    duration_months = serializers.IntegerField()
    current_month = serializers.IntegerField(allow_null=True)
    total_members = serializers.IntegerField()
    pending_payments_count = serializers.IntegerField()
    current_month_summary = PaymentSummarySerializer(allow_null=True)


class OrganizerDashboardSerializer(serializers.Serializer):
    """Complete organizer dashboard"""
    total_chits = serializers.IntegerField()
    chits = OrganizerChitSummarySerializer(many=True)


class PaymentHistorySerializer(serializers.Serializer):
    """Payment history for a member"""
    month_number = serializers.IntegerField()
    amount_paid = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    payment_date = serializers.DateTimeField()
    is_lifter = serializers.BooleanField()


class MemberPaymentHistoryResponseSerializer(serializers.Serializer):
    """Response for member payment history"""
    member_id = serializers.CharField()
    member_type = serializers.CharField()
    payment_history = PaymentHistorySerializer(many=True)


class LiftEligibilitySerializer(serializers.Serializer):
    """Lift eligibility check response"""
    can_lift = serializers.BooleanField()
    reason = serializers.CharField()


class ChitValidationSerializer(serializers.Serializer):
    """Chit validation response"""
    is_valid = serializers.BooleanField()
    issues = serializers.ListField(child=serializers.CharField())


class MonthlyReportSerializer(serializers.Serializer):
    """Complete monthly report"""
    chit_id = serializers.IntegerField()
    title = serializers.CharField()
    total_months = serializers.IntegerField()
    monthly_reports = PaymentSummarySerializer(many=True)


class PaymentReminderSerializer(serializers.Serializer):
    """Payment reminder for a member"""
    payment_id = serializers.IntegerField()
    member = serializers.DictField()
    amount_due = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    days_overdue = serializers.IntegerField()


class PaymentRemindersResponseSerializer(serializers.Serializer):
    """Response for payment reminders"""
    month_number = serializers.IntegerField()
    total_pending = serializers.IntegerField()
    reminders = PaymentReminderSerializer(many=True)


class BulkPaymentUpdateSerializer(serializers.Serializer):
    """Input for bulk payment update"""
    updates = serializers.ListField(
        child=serializers.DictField()
    )
    
    def validate_updates(self, value):
        """Validate each update entry"""
        for update in value:
            if 'payment_id' not in update or 'status' not in update:
                raise serializers.ValidationError(
                    "Each update must have 'payment_id' and 'status'"
                )
            if update['status'] not in ['paid', 'pending', 'late']:
                raise serializers.ValidationError(
                    f"Invalid status: {update['status']}"
                )
        return value


class BulkPaymentUpdateResponseSerializer(serializers.Serializer):
    """Response for bulk payment update"""
    updated_count = serializers.IntegerField()
    updated_payment_ids = serializers.ListField(child=serializers.IntegerField())
    errors = serializers.ListField(child=serializers.DictField())

