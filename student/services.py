# student/services.py

from django.db import transaction
from django.utils import timezone
from accounts.models import User
from provider.models import MessStatus
from .models import ActiveSubscription, Attendance
from django.shortcuts import get_object_or_404 # It's good practice to import this

def mark_student_attendance(student, provider_unique_id):
    """
    Handles all validation and logic for a student scanning a QR code.
    Returns (success_boolean, message_string).
    """
    try:
        provider = User.objects.get(unique_id=provider_unique_id, role='PROVIDER')
    except User.DoesNotExist:
        return False, "Invalid provider QR code."

    # 1. Check if the mess is active
    try:
        mess_status = MessStatus.objects.get(
            provider=provider,
            date=timezone.now().date(),
            is_active=True
        )
        current_meal = mess_status.meal_type
    except MessStatus.DoesNotExist:
        return False, "This mess is not currently active for any meal."
    try:
        # --- THIS IS THE CORRECTED LINE ---
        active_sub = ActiveSubscription.objects.get(
            student_profile__user=student, # Changed from 'student=student'
            mess_plan__provider=provider,
            is_active=True,
            mess_plan__meal_type__in=[current_meal, 'BOTH']
        )
    except ActiveSubscription.DoesNotExist:
        return False, f"You do not have an active subscription for {current_meal.lower()} with this provider."
    except ActiveSubscription.MultipleObjectsReturned:
        return False, "Error: You have multiple active subscriptions with this provider. Please contact support."

    # 3. Check if they have any coupons left
    if active_sub.remaining_coupons <= 0:
        return False, "You have no remaining coupons for this plan."

    # 4. Check if they have already marked attendance for this meal today
    if Attendance.objects.filter(student=student, date=timezone.now().date(), meal_type=current_meal).exists():
        return False, f"You have already marked your attendance for today's {current_meal.lower()}."

    # 5. All checks passed. Mark attendance.
    with transaction.atomic():
        Attendance.objects.create(
            student=student,
            provider=provider,
            mess_plan=active_sub.mess_plan,
            date=timezone.now().date(),
            meal_type=current_meal,
            status=Attendance.Status.PRESENT
        )
        active_sub.remaining_coupons -= 1
        active_sub.save(update_fields=['remaining_coupons'])
        if active_sub.remaining_coupons == 0:
            active_sub.is_active = False


    return True, f"Success! Attendance marked for {current_meal.lower()}. One coupon has been used."