# provider/services.py

from django.db import transaction
from django.utils import timezone
from accounts.models import User
from student.models import ActiveSubscription, StudentHoliday, Attendance
from provider.models import MessHoliday

def mark_absent_students(provider, date, meal_type):
    """
    Finds all subscribed students for a meal, checks who is missing,
    and marks them absent, consuming a coupon.
    """
    # 1. Check if the mess itself was on holiday. If so, do nothing.
    if MessHoliday.objects.filter(provider=provider, date=date, meal_type__in=[meal_type, 'BOTH']).exists():
        print("Mess is on holiday:", provider, date, meal_type)
        return 0

    # 2. Find all students who should have attended
    # This covers students with LUNCH, DINNER, or BOTH plan types correctly
    subscribed_students = ActiveSubscription.objects.filter(
        mess_plan__provider=provider,
        is_active=True,
        mess_plan__meal_type__in=[meal_type, 'BOTH']
    ).values_list('student_id', flat=True)
    # print("Subscribed students:", subscribed_students)

    # 3. Find students who are exempt (already marked present or on leave)
    exempt_students = Attendance.objects.filter(
        provider=provider,
        date=date,
        meal_type=meal_type
    ).values_list('student_id', flat=True)
    # print("Exempt students (already marked):", exempt_students)
    # 4. Find the students who are absent (subscribed but not exempt)
    absent_student_ids = set(subscribed_students) - set(exempt_students)
    # print("Absent student IDs:", absent_student_ids)
    if not absent_student_ids:
        print("No absent students found:", provider, date, meal_type)
        return 0

    # 5. Get the active subscriptions for the absent students
    subscriptions_to_update = ActiveSubscription.objects.filter(
        student_id__in=absent_student_ids,
        mess_plan__provider=provider,
        is_active=True
    )
    # print("Subscriptions to update:", subscriptions_to_update)
    with transaction.atomic():
        for sub in subscriptions_to_update:
            # Create an 'ABSENT' record
            Attendance.objects.create(
                student_id=sub.student_id,
                provider_id=provider,
                mess_plan_id=sub.mess_plan.id,
                date=date,
                meal_type=meal_type,
                status=Attendance.Status.ABSENT
            )
            print(f"Marked absent: Student ID {sub.student_id} provider {provider} for mess plan id {sub.mess_plan.id} on {date} for {meal_type}")
            # Consume a coupon
            if sub.remaining_coupons > 0:
                sub.remaining_coupons -= 1
                if sub.remaining_coupons == 0:
                    sub.is_active = False
                sub.save(update_fields=['remaining_coupons', 'is_active'])
    
    return len(absent_student_ids)

def mark_student_personal_holiday(provider,date, meal_type):
    """
    Marks holidays for students who have applied for it on a given date and meal type.
    """
    # Find all student holidays for the provider on the given date and meal type
    student_holidays = StudentHoliday.objects.filter(
        mess_plan__provider=provider,
        date=date,
        meal_type__in=[meal_type, 'both']
    ).select_related('student', 'mess_plan')

    for holiday in student_holidays:
        # Check if an attendance record already exists
        if not Attendance.objects.filter(
            student=holiday.student,
            provider=provider,
            date=date,
            meal_type=meal_type
        ).exists():
            # Create a 'MESS_HOLIDAY' attendance record
            Attendance.objects.create(
                student=holiday.student,
                provider=provider,
                mess_plan=holiday.mess_plan,
                date=date,
                meal_type=meal_type,
                status=Attendance.Status.PERSONAL_HOLIDAY
            )
            # print(f"Marked mess holiday: Student ID {holiday.student.id} provider {provider} for mess plan id {holiday.mess_plan.id} on {date} for {meal_type}")
    return student_holidays.count()

def mark_student_mess_holiday(provider, date, meal_type):
    """
    Marks holidays for students when the mess itself is on holiday.
    """
    if isinstance(provider, int):
        provider = User.objects.get(id=provider)
    # # Find all active subscriptions for the provider and meal type
    active_subs = ActiveSubscription.objects.filter(
        mess_plan__provider=provider,
        is_active=True,
        mess_plan__meal_type__in=[meal_type, 'BOTH']
    ).select_related('student', 'mess_plan')
    print("Active subscriptions found:",active_subs)
    for sub in active_subs:
        # Check if an attendance record already exists
        if not Attendance.objects.filter(
            student=sub.student.id,
            provider=provider,
            date=date,
            meal_type=meal_type
        ).exists():
            # Create a 'MESS_HOLIDAY' attendance record
            Attendance.objects.create(
                student=sub.student,
                provider=provider,
                mess_plan=sub.mess_plan,
                date=date,
                meal_type=meal_type,
                status=Attendance.Status.MESS_HOLIDAY
            )
            print(f"Marked mess holiday: Student ID {sub.student.id} provider {provider} for mess plan id {sub.mess_plan.id} on {date} for {meal_type}")
    return active_subs.count()