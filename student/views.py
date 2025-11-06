from operator import sub
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import *
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from provider.models import *
from .models import *
import datetime, json
from django.utils import timezone
from datetime import datetime, timedelta, time, date
from django.db import transaction
from django.http import Http404, JsonResponse

@login_required
def student_home(request):
    return render(request, "student/home.html", {"user": request.user})

@login_required
def student_profile(request):
    profile, created = StudentProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        if full_name:
            profile.full_name = full_name

        phone_no = request.POST.get("phone_no")
        if phone_no:
            profile.phone_no = phone_no
            # if hasattr(request.user, 'phone_no'):
            request.user.phone_no = phone_no
            request.user.save()
        
        email = request.POST.get("email")
        if email:
            profile.email = email

        gender = request.POST.get("gender")
        if gender:
            profile.gender = gender

        dob = request.POST.get("dob")
        if dob:
            profile.dob = dob

        address = request.POST.get("address")
        if address:
            profile.address = address

        if 'profile_photo' in request.FILES:
            profile.profile_photo = request.FILES['profile_photo']

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("student_profile")
        
    return render(request, "student/profile.html", {"profile": profile})

@login_required
def student_search_mess(request):
    providers = MessProviderProfile.objects.all()
    query = request.POST.get('query')
    address = request.POST.get('address')
    
    if request.method == "POST":
        search_query = Q()
        if query:
            search_query |= Q(mess_name__icontains=query)
        if address:
            search_query |= Q(address__icontains=address)
        
        if search_query:
            providers = providers.filter(search_query).distinct()
    
    context = {
        'providers': providers,
        'query': query or '',
        'address': address or '',
    }
    return render(request, 'student/search.html', context)

@login_required
def provider_details(request, provider_pk):
    provider = get_object_or_404(MessProviderProfile, pk=provider_pk)
    
    plans = MessPlan.objects.filter(provider=provider.user, is_public=True).order_by('price')
    
    current_request = SubscriptionRequest.objects.filter(
        student=request.user,
        provider=provider.user
    ).exclude(status=SubscriptionRequest.Status.REJECTED).first()

    context = {
        'provider': provider,
        'plans': plans,
        'current_request': current_request,
    }
    return render(request, 'student/provider_details.html', context)

@login_required
def request_subscription(request, plan_id):
    plan = get_object_or_404(MessPlan, pk=plan_id)

    if request.method == "POST":
        existing_request = SubscriptionRequest.objects.filter(
            student=request.user,
            provider=plan.provider
        ).exclude(status=SubscriptionRequest.Status.REJECTED).exists()

        if existing_request:
            messages.warning(request, "You already have a request or active subscription with this provider.")
            return redirect('provider_details', provider_pk=plan.provider.id)

        SubscriptionRequest.objects.create(
            student=request.user,
            plan=plan,
            provider=plan.provider,
            status=SubscriptionRequest.Status.PENDING
        )
        messages.success(request, "Subscription request sent successfully!")
        # return redirect('provider_details', provider_pk=plan.provider.id)
        return redirect("student_home")

    messages.error(request, "Invalid request.")
    return redirect("student_home")

@login_required
def my_subscriptions(request):
    """
    Shows all subscription requests history of a student.
    """
    subscriptions = SubscriptionRequest.objects.filter(
        student=request.user
    ).select_related("plan", "provider").order_by("-created_at")

    context = {"subscriptions": subscriptions}
    return render(request, "student/my_subscriptions.html", context)

@login_required
def active_subscriptions(request):
    """
    Displays the student's currently active mess plan subscriptions.
    """
    student_profile = get_object_or_404(StudentProfile, user=request.user)

    active_subs = (
        ActiveSubscription.objects
        .filter(student_profile=student_profile, is_active=True)
        .select_related("mess_plan__provider__provider_profile")
    )

    subscriptions_data = []
    for sub in active_subs:
        provider_profile = getattr(sub.mess_plan.provider, "provider_profile", None)
        total = sub.total_coupons or 1  # Avoid division by zero
        percent_remaining = (sub.remaining_coupons / total) * 100
        coupon_percentage = round(percent_remaining, 2)
        # in your view
        if coupon_percentage < 25:
            color_class = "bg-danger"
        elif coupon_percentage < 50:
            color_class = "bg-warning"
        else:
            color_class = "bg-success"


        subscriptions_data.append({
            "mess_name": provider_profile.mess_name if provider_profile else "N/A",
            "mess_image": sub.mess_plan.plan_image,
            "phone_no": provider_profile.phone_no if provider_profile else "N/A",
            "mess_type": sub.mess_plan.mess_type,
            "service_type": sub.mess_plan.service_type,
            "address": provider_profile.address if provider_profile else "N/A",
            "activation_date": sub.activation_date.strftime("%Y-%m-%d %H:%M"),
            "remaining_coupons": sub.remaining_coupons,
            "total_coupons": sub.total_coupons,
            "plan_name": sub.mess_plan.plan_name,
            "mess_plan_id": sub.mess_plan.id,
            "provider_user_id": sub.mess_plan.provider.id,
            "coupon_percentage": round(percent_remaining, 2),
            "color_class": color_class  # 👈 Added
        })

    context = {"active_subscriptions": subscriptions_data}
    return render(request, "student/active_subscriptions.html", context)

@login_required
def view_provider_menu(request, provider_id):
    """
    Displays the upcoming daily menus for a specific provider,
    but only if the student has an active subscription to them.
    """
    # First, verify the student has an active subscription to this provider.
    # This is a critical security check.
    is_subscribed = ActiveSubscription.objects.filter(
        student_profile__user=request.user,
        mess_plan__provider__id=provider_id,
        is_active=True
    ).exists()

    if not is_subscribed:
        # If not subscribed, they are not allowed to see the menu.
        raise Http404("You do not have an active subscription with this provider.")

    # If the check passes, get the provider's details and their menus.
    provider = get_object_or_404(User, id=provider_id)
    
    # Get all menus for this provider from today onwards.
    upcoming_menus = DailyMenu.objects.filter(
        provider=provider,
        date__gte=date.today()
    ).order_by('date', 'meal_type')

    context = {
        'provider': provider,
        'upcoming_menus': upcoming_menus,
    }
    return render(request, "student/daily_menu_list.html", context)
def public_provider_menu(request, provider_id):
    """
    Displays the upcoming menus for a specific provider to ANY user.
    This view is public and does not require a subscription.
    """
    # Get the provider's User object
    # We add role='PROVIDER' to ensure we don't accidentally get a student's page
    provider_user = get_object_or_404(User, id=provider_id, role='PROVIDER')

    # Get all menus for this provider from today onwards, sorted chronologically
    upcoming_menus = DailyMenu.objects.filter(
        provider=provider_user,
        date__gte=date.today()
    ).order_by('date', 'meal_type')

    context = {
        'provider': provider_user, # Pass the User object
        'upcoming_menus': upcoming_menus,
    }
    return render(request, "student/public_menu_list.html", context)

@login_required
def student_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    # You can mark them as read here or on a click event
    return render(request, 'student/notifications.html', {'notifications': notifications})

@login_required
def student_holiday(request):
    """
    Allow students to set holidays for their active mess plan.
    Supports multiple dates and meal selection (lunch/dinner/both).
    Enforces 4-hour-before-meal cutoff and notifies provider.
    """
    # Fetch all active subscriptions of the student
    active_subs = ActiveSubscription.objects.filter(
        student_profile__user=request.user,
        is_active=True
    ).select_related('mess_plan__provider__provider_profile')

    if request.method == "POST":
        selected_plan_id = request.POST.get("plan_id")
        # selected_dates = request.POST.getlist("dates[]")
        raw_dates = request.POST.getlist("dates[]")
        if len(raw_dates) == 1 and "," in raw_dates[0]:
            selected_dates = [d.strip() for d in raw_dates[0].split(",")]
        else:
            selected_dates = raw_dates
        meal_type = request.POST.get("meal_type")
        reason = request.POST.get("reason", "")

        if not selected_plan_id:
            messages.error(request, "Please select plan.")
            return redirect("student_holiday")
        elif not selected_dates:
            messages.error(request, "Please select at least one date.")
            return redirect("student_holiday")
        elif meal_type not in ["LUNCH", "DINNER", "BOTH"]:
            messages.error(request, "Please select a valid meal type.")
            return redirect("student_holiday")


        mess_plan = get_object_or_404(MessPlan, id=selected_plan_id)
        provider_user = mess_plan.provider

        # Ensure the selected meal type matches what the plan offers
        plan_meal_type = mess_plan.meal_type
        if meal_type == "LUNCH" and plan_meal_type not in ["LUNCH", "BOTH"]:
            messages.error(request, "This plan does not include lunch.")
            return redirect("student_holiday")
        if meal_type == "DINNER" and plan_meal_type not in ["DINNER", "BOTH"]:
            messages.error(request, "This plan does not include dinner.")
            return redirect("student_holiday")

        # Define default meal times
        meal_times = {
            "LUNCH": time(12, 0),   # 12:00 PM
            "DINNER": time(20, 0),  # 8:00 PM
            "BOTH": time(12, 0)     # earliest meal for combined
        }

        now = timezone.localtime(timezone.now())

        try:
            with transaction.atomic():
                valid_dates = []
                for date_str in selected_dates:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    meal_time = meal_times[meal_type if meal_type != "BOTH" else "LUNCH"]
                    meal_datetime = timezone.make_aware(datetime.combine(date_obj, meal_time))

                    # Check cutoff: must be 4 hours before meal time
                    if now > meal_datetime - timedelta(hours=4):
                        messages.warning(request, f"Cannot set holiday for {date_str} ({meal_type}) — too close to meal time.")
                        return redirect("student_holiday")

                    # Avoid duplicate holiday
                    if StudentHoliday.objects.filter(
                        student=request.user,
                        mess_plan=mess_plan,
                        date=date_obj,
                        meal_type=meal_type
                    ).exists():
                        messages.warning(request, f"Holiday for {date_str} ({meal_type}) already exists.")
                        return redirect("student_holiday")

                    StudentHoliday.objects.create(
                        student=request.user,
                        mess_plan=mess_plan,
                        date=date_obj,
                        meal_type=meal_type,
                        reason=reason
                    )
                    valid_dates.append(date_str)

                if not valid_dates:
                    messages.warning(request, "No holidays were set due to time restrictions or duplicates.")
                    return redirect("student_holiday")

                # Notify provider
                student_profile = getattr(request.user, 'student_profile', None)
                student_name = student_profile.full_name if student_profile else request.user.username
                dates_str = ', '.join(valid_dates)
                meal_label = dict(MessPlan.MealType.choices).get(meal_type, meal_type.capitalize())

                message = (
                    f"Holiday Alert: {student_name} has marked holidays for "
                    f"{dates_str} ({meal_label}) under plan '{mess_plan.plan_name}'."
                )
                if reason:
                    message += f" Reason: {reason}"

                ProviderNotification.objects.create(
                    recipient=provider_user,
                    message=message
                )

            messages.success(request, "Holidays have been set successfully and provider has been notified.")
            return redirect("student_holiday")

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect("student_holiday")

    # GET request: show form and existing holidays
    student_holidays = StudentHoliday.objects.filter(student=request.user).order_by("date")
    return render(request, "student/holiday.html", {
        "active_subs": active_subs,
        "holidays": student_holidays
    })

@login_required
def get_plan_meal_type(request, plan_id):
    """Return meal type for the selected plan (AJAX endpoint)."""
    plan = get_object_or_404(MessPlan, id=plan_id)
    return JsonResponse({"meal_type": plan.meal_type})

@login_required
def delete_student_holiday(request, holiday_id):
    holiday = get_object_or_404(StudentHoliday, id=holiday_id, student=request.user)

    # Combine date with meal time
    now = timezone.localtime(timezone.now())

    # Define approximate meal times (adjust if your app uses different times)
    MEAL_TIMES = {
        "lunch": time(12, 0),         # 12:00 PM
        "dinner": time(20, 0),        # 8:00 PM
        "lunch_dinner": time(12, 0),  # earliest meal time for both
    }

    meal_time = MEAL_TIMES.get(holiday.meal_type, time(12, 0))
    meal_datetime = timezone.make_aware(datetime.combine(holiday.date, meal_time))

    # Check 4-hour rule
    if now > meal_datetime - timedelta(hours=4):
        messages.error(request, f"You can’t delete this holiday now — less than 4 hours before {holiday.meal_type}.")
        return redirect("student_holiday")

    # Save data before deleting for notification
    provider_user = holiday.mess_plan.provider
    mess_plan = holiday.mess_plan
    date_str = holiday.date.strftime("%B %d, %Y")
    meal_label = holiday.get_meal_type_display()

    # Delete the holiday
    holiday.delete()

    # Send notification to provider
    student_profile = getattr(request.user, 'student_profile', None)
    student_name = student_profile.full_name if student_profile else request.user.username

    message = (
        f"Holiday Update: {student_name} has cancelled their holiday for {date_str} ({meal_label}) "
        f"under plan '{mess_plan.plan_name}'."
    )

    ProviderNotification.objects.create(
        recipient=provider_user,
        message=message
    )

    messages.success(request, "Holiday deleted successfully and provider has been notified.")
    return redirect("student_holiday")

from .services import mark_student_attendance

@login_required
def student_scan_qr(request, provider_unique_id):
    """
    This view is triggered when a student scans a provider's QR code.
    It contains all the validation logic for marking attendance.
    """
    if request.user.role != 'STUDENT':
        messages.error(request, "Only students can mark attendance.")
        return redirect('student_home')

    # Call the service function to handle the complex logic
    success, message = mark_student_attendance(
        student=request.user, 
        provider_unique_id=provider_unique_id
    )

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
        
    return redirect('student_home')
@login_required
def student_scan_page_view(request):
    """
    Renders the page that contains the in-app QR code scanner.
    """
    return render(request, 'student/scan_page.html')

@login_required
def student_attendance_history(request):
    attendances = Attendance.objects.filter(student=request.user)
    return render(request, 'student/attendance_history.html', {'attendances': attendances})

