from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils.timezone import now
from django.contrib.auth.decorators import login_required
from .models import Attendance, MealSession, StudentHolidayRequest
from student.models import Subscription


@login_required
def scan_qr(request, subscription_id, meal_type):
    sub = get_object_or_404(Subscription, pk=subscription_id, student=request.user, active=True)
    today = now().date()

    session = MealSession.objects.filter(provider=sub.provider, date=today, meal_type=meal_type, active=True).first()
    if not session:
        messages.error(request, "No active session. Provider has not started yet.")
        return redirect("my_subscriptions")

    att, created = Attendance.objects.get_or_create(
        subscription=sub, student=request.user, provider=sub.provider, date=today, meal_type=meal_type,
        defaults={"session": session, "status": "PRESENT"}
    )
    if created:
        sub.remaining_coupons -= 1
        sub.save()
        messages.success(request, f"Attendance marked for {meal_type}.")
    else:
        messages.warning(request, "Already marked.")
    return redirect("my_subscriptions")


@login_required
def request_holiday(request, subscription_id, meal_type, date):
    sub = get_object_or_404(Subscription, pk=subscription_id, student=request.user, active=True)
    StudentHolidayRequest.objects.create(subscription=sub, meal_type=meal_type, date=date)
    messages.success(request, "Holiday requested.")
    return redirect("my_subscriptions")
