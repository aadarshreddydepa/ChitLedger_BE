"""
Utility Functions for Chit Fund Management
Helper functions for calculations, validations, and data processing
"""

from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from .models import Chit, ChitSchedule, Payment, Membership, ExternalMember


def calculate_current_month(chit):
    """
    Calculate which month number the chit is currently in
    
    Args:
        chit: Chit object
    
    Returns:
        int: Current month number (1 to duration_months) or None if not started/completed
    """
    if not chit.start_date:
        return None
    
    today = datetime.now().date()
    
    # Chit hasn't started yet
    if today < chit.start_date:
        return None
    
    # Calculate months elapsed
    months_elapsed = (
        (today.year - chit.start_date.year) * 12 + 
        (today.month - chit.start_date.month) + 1
    )
    
    # Chit completed
    if months_elapsed > chit.duration_months:
        return None
    
    return months_elapsed


def get_available_slots(chit):
    """
    Calculate how many slots are still available in a chit
    
    Args:
        chit: Chit object
    
    Returns:
        tuple: (used_slots, available_slots)
    """
    # Count verified member slots
    verified_slots = Membership.objects.filter(chit=chit).aggregate(
        total=Sum('slot_count')
    )['total'] or 0
    
    # Count external member slots
    external_slots = ExternalMember.objects.filter(chit=chit).aggregate(
        total=Sum('slot_count')
    )['total'] or 0
    
    used_slots = verified_slots + external_slots
    available_slots = chit.total_slots - used_slots
    
    return used_slots, available_slots


def get_members_list(chit):
    """
    Get unified list of all members (verified + external) with their details
    
    Args:
        chit: Chit object
    
    Returns:
        list: List of dicts with member information
    """
    members = []
    
    # Add verified members
    for membership in Membership.objects.filter(chit=chit).select_related('user'):
        members.append({
            'id': membership.membership_id,
            'type': 'verified',
            'name': membership.user.name,
            'phone_number': membership.user.phone_number,
            'slot_count': membership.slot_count,
            'is_organizer': membership.is_organizer,
            'joined_date': membership.joined_date
        })
    
    # Add external members
    for external in ExternalMember.objects.filter(chit=chit):
        members.append({
            'id': external.member_id,
            'type': 'external',
            'name': external.name or 'Unknown',
            'phone_number': external.phone_number,
            'slot_count': external.slot_count,
            'is_organizer': external.is_organizer,
            'joined_date': external.joined_date
        })
    
    return members


def calculate_payment_summary(chit, month_number):
    """
    Calculate payment summary for a specific month
    
    Args:
        chit: Chit object
        month_number: Month number (1 to duration_months)
    
    Returns:
        dict: Payment statistics including expected, collected, pending counts
    """
    # Get schedule for this month
    schedule = ChitSchedule.objects.filter(
        chit=chit, 
        month_number=month_number
    ).first()
    
    if not schedule:
        return None
    
    # Get all payments for this month
    payments = Payment.objects.filter(chit_schedule=schedule)
    
    # Calculate total expected (all non-lifters pay)
    total_expected = schedule.no_lift_amount * (chit.total_slots - 1)
    
    # Calculate total collected (sum of positive payments only)
    total_collected = payments.filter(
        status='paid', 
        amount_paid__gt=0
    ).aggregate(
        total=Sum('amount_paid')
    )['total'] or Decimal('0')
    
    # Count payments by status
    paid_count = payments.filter(status='paid').count()
    pending_count = payments.filter(status='pending').count()
    late_count = payments.filter(status='late').count()
    
    # Get lifter information
    lifter_info = None
    if schedule.lifted_by_membership:
        lifter_info = {
            'name': schedule.lifted_by_membership.user.name,
            'type': 'verified'
        }
    elif schedule.lifted_by_external:
        lifter_info = {
            'name': schedule.lifted_by_external.name,
            'type': 'external'
        }
    
    return {
        'month_number': month_number,
        'lift_amount': str(schedule.lift_amount),
        'no_lift_amount': str(schedule.no_lift_amount),
        'total_expected': str(total_expected),
        'total_collected': str(total_collected),
        'balance': str(total_expected - total_collected),
        'paid_count': paid_count,
        'pending_count': pending_count,
        'late_count': late_count,
        'lifter': lifter_info
    }


def get_member_payment_history(chit, member_id, member_type):
    """
    Get payment history for a specific member in a chit
    
    Args:
        chit: Chit object
        member_id: Member ID (int or str)
        member_type: 'verified' or 'external'
    
    Returns:
        list: List of payment records with details
    """
    if member_type == 'verified':
        payments = Payment.objects.filter(
            chit_schedule__chit=chit,
            membership_id=member_id
        ).select_related('chit_schedule').order_by('month_number')
    else:  # external
        payments = Payment.objects.filter(
            chit_schedule__chit=chit,
            external_member_id=member_id
        ).select_related('chit_schedule').order_by('month_number')
    
    history = []
    for payment in payments:
        history.append({
            'month_number': payment.month_number,
            'amount_paid': str(payment.amount_paid),
            'status': payment.status,
            'payment_date': payment.payment_date,
            'is_lifter': payment.amount_paid < 0  # Negative amount means they lifted
        })
    
    return history


def check_if_member_can_lift(chit, member_id, member_type):
    """
    Check if a member is eligible to lift in the chit
    A member can't lift if they've already lifted before
    
    Args:
        chit: Chit object
        member_id: Member ID (int or str)
        member_type: 'verified' or 'external'
    
    Returns:
        tuple: (can_lift: bool, reason: str)
    """
    # Check if member already lifted
    if member_type == 'verified':
        already_lifted = ChitSchedule.objects.filter(
            chit=chit,
            lifted_by_membership_id=member_id
        ).exists()
    else:
        already_lifted = ChitSchedule.objects.filter(
            chit=chit,
            lifted_by_external_id=member_id
        ).exists()
    
    if already_lifted:
        return False, "Member has already lifted in this chit"
    
    return True, "Eligible to lift"


def validate_chit_completion(chit):
    """
    Validate if all months have been properly assigned and paid
    
    Args:
        chit: Chit object
    
    Returns:
        tuple: (is_valid: bool, issues: list)
    """
    issues = []
    
    # Check if all months have lifters assigned
    unassigned_months = ChitSchedule.objects.filter(
        chit=chit,
        lifted_by_membership__isnull=True,
        lifted_by_external__isnull=True
    ).count()
    
    if unassigned_months > 0:
        issues.append(f"{unassigned_months} month(s) don't have lifters assigned")
    
    # Check if all payments are completed
    pending_payments = Payment.objects.filter(
        chit_schedule__chit=chit,
        status__in=['pending', 'late']
    ).count()
    
    if pending_payments > 0:
        issues.append(f"{pending_payments} payment(s) are still pending or late")
    
    # Check if all months have at least one payment record
    schedules_without_payments = ChitSchedule.objects.filter(
        chit=chit
    ).annotate(
        payment_count=Count('payments')
    ).filter(payment_count=0).count()
    
    if schedules_without_payments > 0:
        issues.append(f"{schedules_without_payments} month(s) have no payment records")
    
    return len(issues) == 0, issues


def get_chit_dashboard_data(chit):
    """
    Get comprehensive dashboard data for a chit
    
    Args:
        chit: Chit object
    
    Returns:
        dict: Complete chit information with members, schedules, and summaries
    """
    current_month = calculate_current_month(chit)
    used_slots, available_slots = get_available_slots(chit)
    members = get_members_list(chit)
    
    # Get payment summary for current month if applicable
    current_month_summary = None
    if current_month:
        current_month_summary = calculate_payment_summary(chit, current_month)
    
    # Get all schedules with lift status
    schedules = []
    for schedule in ChitSchedule.objects.filter(chit=chit).order_by('month_number'):
        lifter_name = None
        if schedule.lifted_by_membership:
            lifter_name = schedule.lifted_by_membership.user.name
        elif schedule.lifted_by_external:
            lifter_name = schedule.lifted_by_external.name
        
        schedules.append({
            'month_number': schedule.month_number,
            'lift_amount': str(schedule.lift_amount),
            'no_lift_amount': str(schedule.no_lift_amount),
            'is_lifted': schedule.lifted_by_membership_id is not None or schedule.lifted_by_external_id is not None,
            'lifter_name': lifter_name
        })
    
    return {
        'chit_id': chit.chit_id,
        'title': chit.title,
        'organizer': {
            'name': chit.organizer.name,
            'phone': chit.organizer.phone_number
        },
        'total_slots': chit.total_slots,
        'used_slots': used_slots,
        'available_slots': available_slots,
        'total_amount': str(chit.total_amount),
        'lift_amount': str(chit.lift_amount),
        'start_date': chit.start_date,
        'duration_months': chit.duration_months,
        'current_month': current_month,
        'current_month_summary': current_month_summary,
        'members': members,
        'schedules': schedules
    }


def generate_payment_expectations(chit_schedule):
    """
    Generate expected payment records for all members for a given month
    This can be called at the start of each month to pre-populate payment records
    
    Args:
        chit_schedule: ChitSchedule object for a specific month
    
    Returns:
        list: List of created Payment objects
    """
    chit = chit_schedule.chit
    month_number = chit_schedule.month_number
    payments_created = []
    
    # Get lifter for this month
    lifter_membership_id = chit_schedule.lifted_by_membership_id
    lifter_external_id = chit_schedule.lifted_by_external_id
    
    # Create payment expectations for verified members
    for membership in Membership.objects.filter(chit=chit):
        if membership.membership_id == lifter_membership_id:
            # Lifter receives money (negative amount)
            amount = -(chit.total_amount - chit_schedule.lift_amount)
        else:
            # Non-lifter pays
            amount = chit_schedule.no_lift_amount * membership.slot_count
        
        payment, created = Payment.objects.get_or_create(
            membership=membership,
            chit_schedule=chit_schedule,
            month_number=month_number,
            defaults={
                'amount_paid': amount,
                'status': 'pending'
            }
        )
        if created:
            payments_created.append(payment)
    
    # Create payment expectations for external members
    for external in ExternalMember.objects.filter(chit=chit):
        if external.member_id == lifter_external_id:
            # Lifter receives money (negative amount)
            amount = -(chit.total_amount - chit_schedule.lift_amount)
        else:
            # Non-lifter pays
            amount = chit_schedule.no_lift_amount * external.slot_count
        
        payment, created = Payment.objects.get_or_create(
            external_member=external,
            chit_schedule=chit_schedule,
            month_number=month_number,
            defaults={
                'amount_paid': amount,
                'status': 'pending'
            }
        )
        if created:
            payments_created.append(payment)
    
    return payments_created


def get_monthly_payment_status(chit, month_number):
    """
    Get detailed payment status for a specific month
    Shows which members have paid and which haven't
    
    Args:
        chit: Chit object
        month_number: Month number
    
    Returns:
        dict: Detailed payment status for each member
    """
    schedule = ChitSchedule.objects.filter(
        chit=chit,
        month_number=month_number
    ).first()
    
    if not schedule:
        return None
    
    payments = Payment.objects.filter(
        chit_schedule=schedule
    ).select_related('membership__user', 'external_member')
    
    payment_status = []
    for payment in payments:
        if payment.membership:
            member_info = {
                'id': payment.membership.membership_id,
                'type': 'verified',
                'name': payment.membership.user.name,
                'phone': payment.membership.user.phone_number,
                'slots': payment.membership.slot_count
            }
        else:
            member_info = {
                'id': payment.external_member.member_id,
                'type': 'external',
                'name': payment.external_member.name,
                'phone': payment.external_member.phone_number,
                'slots': payment.external_member.slot_count
            }
        
        payment_status.append({
            'member': member_info,
            'amount_paid': str(payment.amount_paid),
            'status': payment.status,
            'payment_date': payment.payment_date,
            'is_lifter': payment.amount_paid < 0
        })
    
    return {
        'month_number': month_number,
        'schedule': {
            'lift_amount': str(schedule.lift_amount),
            'no_lift_amount': str(schedule.no_lift_amount)
        },
        'payments': payment_status
    }


def calculate_member_total_contribution(chit, member_id, member_type):
    """
    Calculate total amount contributed by a member across all months
    
    Args:
        chit: Chit object
        member_id: Member ID
        member_type: 'verified' or 'external'
    
    Returns:
        dict: Total contributed, total received, net amount
    """
    if member_type == 'verified':
        payments = Payment.objects.filter(
            chit_schedule__chit=chit,
            membership_id=member_id
        )
    else:
        payments = Payment.objects.filter(
            chit_schedule__chit=chit,
            external_member_id=member_id
        )
    
    total_paid = Decimal('0')
    total_received = Decimal('0')
    
    for payment in payments:
        if payment.amount_paid > 0:
            total_paid += payment.amount_paid
        else:
            total_received += abs(payment.amount_paid)
    
    return {
        'total_paid': str(total_paid),
        'total_received': str(total_received),
        'net_amount': str(total_paid - total_received),
        'payment_count': payments.count()
    }