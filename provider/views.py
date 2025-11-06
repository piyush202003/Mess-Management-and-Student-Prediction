from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from accounts.models import *
from django.contrib import messages
from .models import *
from student.models import *
from django.db import transaction
from django.db.models import Prefetch
from django.db.models import Q,F
from django.http import Http404, HttpResponseForbidden, JsonResponse
import json
from datetime import timedelta,date
from datetime import datetime
import qrcode
import io
import base64
from .decorators import provider_required
from .services import *
from .forms import *


@login_required
@provider_required
def provider_home(request):
    provider_profile = get_object_or_404(MessProviderProfile, user=request.user)
    menu_items = MenuItem.objects.filter(provider=request.user)

    # Use the server's local timezone (e.g., Asia/Kolkata)
    local_now = timezone.localtime(timezone.now())
    today = local_now.date()

    # --- Time Window Logic ---
    # start_window_delta = timedelta(hours=2)
    # stop_grace_period = timedelta(hours=2)
    start_window_delta = timedelta(hours=0)
    stop_grace_period = timedelta(hours=0)

    # --- LUNCH CONTEXT ---
    can_start_lunch = can_stop_lunch = False
    is_lunch_time_over = False

    if provider_profile.lunch_start and provider_profile.lunch_end:
        lunch_start_dt = timezone.make_aware(datetime.datetime.combine(today, provider_profile.lunch_start))
        lunch_end_dt = timezone.make_aware(datetime.datetime.combine(today, provider_profile.lunch_end))
        lunch_start_activation = lunch_start_dt - start_window_delta
        lunch_stop_deactivation = lunch_end_dt

        can_start_lunch = lunch_start_activation <= local_now <= lunch_end_dt
        is_lunch_time_over = local_now > lunch_end_dt
        can_stop_lunch = local_now <= lunch_stop_deactivation
    else:
        messages.warning(request, "Lunch timings are not set in your profile.")

    # --- DINNER CONTEXT ---
    can_start_dinner = can_stop_dinner = False
    is_dinner_time_over = False

    if provider_profile.dinner_start and provider_profile.dinner_end:
        dinner_start_dt = timezone.make_aware(datetime.datetime.combine(today, provider_profile.dinner_start))
        dinner_end_dt = timezone.make_aware(datetime.datetime.combine(today, provider_profile.dinner_end))
        if dinner_end_dt < dinner_start_dt:
            dinner_end_dt += timedelta(days=1)
        dinner_start_activation = dinner_start_dt - start_window_delta
        dinner_stop_deactivation = dinner_end_dt + stop_grace_period

        can_start_dinner = dinner_start_activation <= local_now <= dinner_end_dt
        is_dinner_time_over = local_now > dinner_end_dt
        can_stop_dinner = local_now <= dinner_stop_deactivation
    else:
        messages.warning(request, "Dinner timings are not set in your profile.")

    # --- Mess Status ---
    lunch_status, _ = MessStatus.objects.get_or_create(provider=request.user, date=today, meal_type='LUNCH')
    dinner_status, _ = MessStatus.objects.get_or_create(provider=request.user, date=today, meal_type='DINNER')

    # ⚡ Check if provider already declared holidays
    lunch_holiday_exists = MessHoliday.objects.filter(provider=request.user, date=today, meal_type='LUNCH').exists()
    dinner_holiday_exists = MessHoliday.objects.filter(provider=request.user, date=today, meal_type='DINNER').exists()

    if lunch_holiday_exists:
        messages.warning(request, "Lunch has already been marked as a holiday for today.")
        # Prevent accidental re-activation
        can_start_lunch = can_stop_lunch = False

    if dinner_holiday_exists:
        messages.warning(request, "Dinner has already been marked as a holiday for today.")
        can_start_dinner = can_stop_dinner = False

    # --- Auto-holiday logic (only if not already a holiday) ---
    if not lunch_holiday_exists and is_lunch_time_over and lunch_status.started_at is None and not lunch_status.stopped_at:
        mark_student_mess_holiday(provider=request.user.id,date=today, meal_type='LUNCH')
        MessHoliday.objects.create(provider=request.user, date=today, meal_type='LUNCH',
                                   reason='Auto-created: Mess not started.')
        messages.warning(request, "Lunch was not started and has been marked as a holiday.")
        _send_notifications_to_subscribed_students(
            provider=request.user,
            subject="Lunch Holiday Notice",
            message="Lunch mess has been marked as a holiday for today as it was not started on time.",
            menu_items=None
        )
        lunch_status.stopped_at = timezone.now()
        lunch_status.save()
        

    if not dinner_holiday_exists and is_dinner_time_over and dinner_status.started_at is None and not dinner_status.stopped_at:
        mark_student_mess_holiday(provider=request.user.id, date=today, meal_type='DINNER')
        MessHoliday.objects.create(provider=request.user, date=today, meal_type='DINNER',
                                   reason='Auto-created: Mess not started.')
        messages.warning(request, "Dinner was not started and has been marked as a holiday.")
        _send_notifications_to_subscribed_students(
            provider=request.user,
            subject="Dinner Holiday Notice",
            message="Dinner mess has been marked as a holiday for today as it was not started on time.",
            menu_items=None
        )
        dinner_status.stopped_at = timezone.now()
        dinner_status.save()
        

    # --- Auto-stop logic ---
    if lunch_status.is_active and not can_stop_lunch:
        lunch_status.is_active = False
        lunch_status.stopped_at = timezone.now()
        lunch_status.save()
        mark_absent_students(provider=request.user.id, date=today, meal_type='LUNCH')
        mark_student_personal_holiday(provider=request.user.id, date=today, meal_type='LUNCH')
        messages.info(request, "The lunch service has been automatically closed.")

    if dinner_status.is_active and not can_stop_dinner:
        dinner_status.is_active = False
        dinner_status.stopped_at = timezone.now()
        dinner_status.save()
        mark_absent_students(provider=request.user.id, date=today, meal_type='DINNER')
        mark_student_mess_holiday(provider=request.user.id, date=today, meal_type='DINNER')
        messages.info(request, "The dinner service has been automatically closed.")

    context = {
        'provider_profile': provider_profile,
        'menu_items': menu_items,
        'lunch_status': lunch_status,
        'dinner_status': dinner_status,
        'can_start_lunch': can_start_lunch,
        'can_stop_lunch': can_stop_lunch,
        'is_lunch_time_over': is_lunch_time_over,
        'can_start_dinner': can_start_dinner,
        'can_stop_dinner': can_stop_dinner,
        'is_dinner_time_over': is_dinner_time_over,
        'today': today,
    }
    return render(request, "provider/home.html", context)



@login_required
def provider_profile(request):
    profile, created = MessProviderProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        # Update profile fields only if a value is submitted in the POST request
        full_name = request.POST.get("full_name")
        if full_name:
            profile.full_name = full_name
        phone_no = request.POST.get("phone_no")
        if phone_no:
            profile.phone_no = phone_no
        email = request.POST.get("email")
        if email:
            profile.email = email
        service_type = request.POST.get("service_type")
        if service_type:
            profile.service_type = service_type
        mess_type = request.POST.get("mess_type")
        if mess_type:
            profile.mess_type = mess_type
        address = request.POST.get("address")
        if address:
            profile.address = address
        lunch_start = request.POST.get("lunch_start")
        if lunch_start:
            profile.lunch_start = lunch_start
        lunch_end = request.POST.get("lunch_end")
        if lunch_end:
            profile.lunch_end = lunch_end
        dinner_start = request.POST.get("dinner_start")
        if dinner_start:
            profile.dinner_start = dinner_start
        dinner_end = request.POST.get("dinner_end")
        if dinner_end:
            profile.dinner_end = dinner_end
        mess_name = request.POST.get("mess_name")
        if mess_name:
            profile.mess_name = mess_name
        # Handle file uploads
        if 'mess_photo' in request.FILES:
            profile.mess_photo = request.FILES['mess_photo']

        user = request.user
        if profile.phone_no: # Check if profile.phone_no has a value
            # if hasattr(user, 'phone_no'):
                user.phone_no = profile.phone_no
                user.save()

        profile.save()
        messages.success(request, "Profile updated successfully!")
        return redirect("provider_profile")

    return render(request, "provider/profile.html", {"profile": profile})


@login_required
def provider_qr_page(request):
    """Generates and displays the provider's unique QR code."""
    # We will use the provider's unique_id from the User model for the QR data
    user_unique_id = request.user.unique_id
    if not user_unique_id:
        messages.error(request, "Your unique ID is not set. Please contact support.")
        return redirect('provider_home')

    # Construct the URL the student will be directed to
    scan_url = request.build_absolute_uri(reverse('student_scan_qr', args=[user_unique_id]))
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(scan_url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    
    # Convert image to base64 string to embed in HTML
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "provider/qr_page.html", {"qr_image": qr_image_base64})


@login_required
def provider_plans(request):
    """
    Allows a mess provider to create and view their meal plans.
    """
    if request.method == "POST":
        # Check if the user is a provider.
        if request.user.role != 'PROVIDER':
            messages.error(request, "You do not have permission to create plans.")
            return redirect('provider_home')

        try:
            # --- New Logic for the checkbox ---
            is_public_status = 'is_public' in request.POST

            # Create a new MessPlan instance from form data
            new_plan = MessPlan(
                provider=request.user,
                plan_name=request.POST.get("plan_name"),
                plan_type=request.POST.get("plan_type"),
                meal_type=request.POST.get("meal_type"),
                service_type=request.POST.get("service_type"),
                mess_type=request.POST.get("mess_type"),
                coupons=request.POST.get("coupons"),
                price=request.POST.get("price"),
                description=request.POST.get("description"),
                is_public=is_public_status, # Add the new field here
            )
            # Handle food image upload
            if 'plan_image' in request.FILES:
                new_plan.plan_image = request.FILES['plan_image']
            
            # Note: Hardcoding a default path like this is not recommended. 
            # The model's `default` attribute is a better approach.
            else:
                new_plan.plan_image ="D:\\python\\django_practice\\FinalYear\\media\\providers\\default_plan.jpg"

            new_plan.full_clean()  # Validate the model fields
            new_plan.save()
            messages.success(request, "Meal plan created successfully!")
            return redirect("provider_plans")

        except Exception as e:
            messages.error(request, f"Error creating plan: {e}")
            return redirect("provider_plans")
    
    # For GET request, display the form and list existing plans
    plans = MessPlan.objects.filter(provider=request.user).order_by('-created_at')
    
    # Get choices for dropdowns directly from the model
    plan_types = MessPlan.PlanType.choices
    meal_types = MessPlan.MealType.choices
    service_types = MessPlan.ServiceType.choices
    mess_types = MessPlan.MessType.choices

    context = {
        "plans": plans,
        "plan_types": plan_types,
        "meal_types": meal_types,
        "service_types": service_types,
        "mess_types": mess_types,
    }
    return render(request, "provider/plans.html", context)

@login_required
def update_plan(request, pk):
    """
    Displays the update form and processes the update.
    If the plan has active subscriptions, only the public/private status can be changed.
    """
    plan = get_object_or_404(MessPlan, pk=pk, provider=request.user)
    
    # --- Final Check ---
    # This now uses your actual ActiveSubscription model to perform the check.
    has_active_subscriptions = ActiveSubscription.objects.filter(mess_plan=plan, is_active=True).exists()

    if request.method == "POST":
        if has_active_subscriptions:
            # Logic for when subscriptions exist: only update visibility
            plan.is_public = 'is_public' in request.POST
        
            plan.save(update_fields=['is_public', 'updated_at'])
            messages.info(request, "Plan visibility updated (Public/Private). Other details are locked due to active subscriptions.")
            return redirect("provider_plans")
        
        else:
            # Original logic for when no subscriptions exist: full update
            try:
                with transaction.atomic():
                    plan.plan_name = request.POST.get("plan_name") or plan.plan_name
                    # ( ... all other fields ... )
                    plan.description = request.POST.get("description") or plan.description
                    plan.is_public = 'is_public' in request.POST
                    
                    if 'plan_image' in request.FILES:
                        plan.plan_image = request.FILES['plan_image']
                    
                    plan.full_clean()
                    plan.save()
                messages.success(request, "Meal plan updated successfully!")
                return redirect("provider_plans")
            except Exception as e:
                messages.error(request, f"Error updating plan: {e}")
                return redirect("provider_plans")

    # For GET request, pass the subscription status to the template
    plan_types = MessPlan.PlanType.choices
    meal_types = MessPlan.MealType.choices
    service_types = MessPlan.ServiceType.choices
    mess_types = MessPlan.MessType.choices

    context = {
        "plan": plan,
        "plan_types": plan_types,
        "meal_types": meal_types,
        "service_types": service_types,
        "mess_types": mess_types,
        "has_active_subscriptions": has_active_subscriptions, # This is now accurate
    }
    return render(request, "provider/update_plan.html", context)

@login_required
def delete_plan(request, pk):
    """
    Deletes a specific mess plan, but only if it has no active subscriptions.
    """
    plan = get_object_or_404(MessPlan, pk=pk, provider=request.user)

    # --- Final Check ---
    # This now uses your actual ActiveSubscription model to perform the check.
    has_active_subscriptions = ActiveSubscription.objects.filter(mess_plan=plan, is_active=True).exists()

    if has_active_subscriptions:
        messages.error(request, "This plan cannot be deleted because it has active student subscriptions.")
        return redirect("provider_plans")
    
    if request.method == "POST":
        plan.delete()
        messages.success(request, "Meal plan deleted successfully!")
        return redirect("provider_plans")
    
    return redirect("provider_plans")

@login_required
@provider_required # It's good practice to add your decorator here
def manage_requests(request):
    """
    Show all subscription requests for this provider, with filtering.
    """
    # 1. Get search parameters from the request's GET parameters
    student_query = request.GET.get('student', '')
    plan_id = request.GET.get('plan', '')
    status = request.GET.get('status', '')

    # 2. Start with the base, optimized queryset for this provider
    requests_list = SubscriptionRequest.objects.filter(
        provider=request.user
    ).select_related('student', 'plan')

    # 3. Apply filters conditionally
    if student_query:
        requests_list = requests_list.filter(
            Q(student__username__icontains=student_query) |
            Q(student__first_name__icontains=student_query) |
            Q(student__last_name__icontains=student_query)
        )
    
    if plan_id:
        requests_list = requests_list.filter(plan__id=plan_id)
        
    if status:
        requests_list = requests_list.filter(status=status)
    
    # 4. Get data for the filter dropdowns
    available_plans = MessPlan.objects.filter(provider=request.user).distinct()
    status_choices = SubscriptionRequest.Status.choices

    context = {
        "requests": requests_list.order_by('-created_at'),
        "available_plans": available_plans,
        "status_choices": status_choices,
    }
    return render(request, "provider/manage_requests.html", context)
@login_required
def update_request_status(request, request_id, action):
    """
    Provider can accept or reject a subscription request.
    """
    sub_request = get_object_or_404(SubscriptionRequest, pk=request_id, provider=request.user)

    if action == "accept":
        with transaction.atomic():
            sub_request.status = SubscriptionRequest.Status.ACCEPTED
            sub_request.save()
            messages.success(request, f"Subscription request from {sub_request.student.username} accepted.")

            # Find the corresponding StudentProfile
            student_profile = StudentProfile.objects.get(user=sub_request.student)

            # Create and save the ActiveSubscription
            ActiveSubscription.objects.create(
                student_profile=student_profile,
                student=sub_request.student,
                provider_id=request.user.id,
                mess_plan=sub_request.plan,
                total_coupons=sub_request.plan.coupons,
                remaining_coupons=sub_request.plan.coupons
            )

    elif action == "reject":
        sub_request.status = SubscriptionRequest.Status.REJECTED
        sub_request.save()
        messages.warning(request, f"Subscription request from {sub_request.student.username} rejected.")
    else:
        messages.error(request, "Invalid action.")
        return redirect("manage_requests")

    return redirect("manage_requests")

    
@login_required
def menu_list(request):
    query = request.GET.get("q")
    special = request.GET.get("special")
    menu_items = MenuItem.objects.filter(provider=request.user)
    if query:
        menu_items = menu_items.filter(dish_name__icontains=query)
    if special:
        menu_items = menu_items.filter(is_special=True)
    return render(request, "provider/menu_list.html", {"menu_items": menu_items})

@login_required
def menu_create(request):
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            dish_name = form.cleaned_data['dish_name']
            if MenuItem.objects.filter(provider=request.user, dish_name__iexact=dish_name).exists():
                messages.error(request, "❌ Dish with this name already exists.")
            else:
                menu_item = form.save(commit=False)
                menu_item.provider = request.user
                if not menu_item.dish_image:
                    menu_item.dish_image = "providers/default_menu.jpg"
                menu_item.save()
                messages.success(request, "✅ Dish added successfully.")
                return redirect("menu_list")
    else:
        form = MenuItemForm()
    return render(request, "provider/menu_form.html", {"form": form})

@login_required
def menu_update(request, pk):
    menu_item = get_object_or_404(MenuItem, pk=pk, provider=request.user)
    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
        if form.is_valid():
            dish_name = form.cleaned_data['dish_name']
            if MenuItem.objects.filter(provider=request.user, dish_name__iexact=dish_name).exclude(pk=menu_item.pk).exists():
                messages.error(request, "❌ Dish with this name already exists.")
            else:
                form.save()
                messages.success(request, "✅ Dish updated successfully.")
                return redirect("menu_list")
    else:
        form = MenuItemForm(instance=menu_item)
    return render(request, "provider/menu_form.html", {"form": form, "menu_item": menu_item})
@login_required
def menu_delete(request, pk):
    menu_item = get_object_or_404(MenuItem, pk=pk, provider=request.user)
    menu_item.delete()
    messages.success(request, "Dish deleted successfully.")
    return redirect("menu_list")

@login_required
@provider_required
def manage_students(request):
    """
    Displays a list of students with active subscriptions for the current provider,
    with added search and filter functionality.
    """
    # 1. Get search parameters from the request.GET dictionary
    name_phone_query = request.GET.get('name_phone', '')
    plan_id = request.GET.get('plan', '')
    activation_date = request.GET.get('activation_date', '')

    # 2. Start with the base queryset for this provider
    active_subscriptions = ActiveSubscription.objects.filter(
        mess_plan__provider=request.user,
        is_active=True
    ).select_related(
        'student',
        'mess_plan'
    )

    # 3. Apply filters conditionally based on search input
    if name_phone_query:
        # Use Q objects to search in multiple fields (OR condition)
        active_subscriptions = active_subscriptions.filter(
            Q(student__first_name__icontains=name_phone_query) |
            Q(student__last_name__icontains=name_phone_query) |
            Q(student__username__icontains=name_phone_query) |
            Q(student__phone__icontains=name_phone_query)
        )
    
    if plan_id:
        active_subscriptions = active_subscriptions.filter(mess_plan__id=plan_id)
        
    if activation_date:
        # Filter where the date part of the datetime field matches
        active_subscriptions = active_subscriptions.filter(activation_date__date=activation_date)
    
    # 4. Get all unique plans for this provider to populate the filter dropdown
    available_plans = MessPlan.objects.filter(provider=request.user).distinct()

    context = {
        "active_subscriptions": active_subscriptions.order_by('-activation_date'),
        "available_plans": available_plans,
    }
    return render(request, "provider/manage_students.html", context)
from django.utils.dateparse import parse_date

@login_required
@provider_required
def provider_student_detail_view(request, student_id):
    student = get_object_or_404(
        User.objects.select_related('student_profile'), 
        id=student_id, 
        role='STUDENT'
    )
    if not ActiveSubscription.objects.filter(student=student, mess_plan__provider=request.user).exists():
        raise Http404("You do not have permission to view this student's details.")

    try:
        active_subscription = ActiveSubscription.objects.get(
            student=student, 
            mess_plan__provider=request.user,
            is_active=True
        )
    except ActiveSubscription.DoesNotExist:
        active_subscription = None

    # --- New: Get Query Params ---
    date_query = request.GET.get('date')
    plan_query = request.GET.get('plan')

    attendance_qs = Attendance.objects.filter(
        student=student, provider=request.user
    ).select_related('mess_plan')

    if date_query:
        parsed_date = parse_date(date_query)
        if parsed_date:
            attendance_qs = attendance_qs.filter(date=parsed_date)
    if plan_query:
        attendance_qs = attendance_qs.filter(mess_plan__id=plan_query)

    attendance_history = attendance_qs.order_by('-date', '-marked_at')

    # Fetch all available plans for filter dropdown
    student_plans = (
        Attendance.objects
        .filter(student=student, provider=request.user)
        .values('mess_plan__id', 'mess_plan__plan_name')
        .distinct()
    )

    context = {
        'student': student,
        'attendance_history': attendance_history,
        'active_subscription': active_subscription,
        'student_plans': student_plans,
        'selected_date': date_query or '',
        'selected_plan': int(plan_query) if plan_query else '',
    }
    return render(request, 'provider/student_detail.html', context)
@login_required
@provider_required
def increase_student_coupons(request, subscription_id):
    """
    Handles the POST request to increase a student's remaining coupons,
    but ensures it doesn't exceed the total coupon limit.
    """
    if request.method != 'POST':
        return HttpResponseForbidden("Invalid request method.")

    # 1. Get the subscription and perform security check
    subscription = get_object_or_404(ActiveSubscription, id=subscription_id)

    # SECURITY: Ensure the provider owns this subscription
    if subscription.mess_plan.provider != request.user:
        messages.error(request, "You do not have permission to modify this subscription.")
        return redirect('manage_students')

    # 2. Validate input
    try:
        coupons_to_add = int(request.POST.get('coupons_to_add', 0))
        if coupons_to_add <= 0:
            messages.error(request, "Please enter a positive number of coupons to add.")
            return redirect('provider_student_detail', student_id=subscription.student.id)
    except (ValueError, TypeError):
        messages.error(request, "Invalid number entered for coupons.")
        return redirect('provider_student_detail', student_id=subscription.student.id)

    # 3. Calculate new remaining coupons (without exceeding total)
    new_remaining = subscription.remaining_coupons + coupons_to_add

    if new_remaining > subscription.total_coupons:
        # Cap at total_coupons
        new_remaining = subscription.total_coupons
        messages.warning(
            request,
            f"You tried to add {coupons_to_add} coupons, "
            f"but remaining coupons cannot exceed total ({subscription.total_coupons}). "
            f"It has been capped at {subscription.total_coupons}."
        )
    else:
        messages.success(request, f"Successfully added {coupons_to_add} coupons for {subscription.student.username}.")

    # 4. Save the updated value
    subscription.remaining_coupons = new_remaining
    subscription.save(update_fields=["remaining_coupons"])
    _send_notifications_to_subscribed_students(
        provider=request.user,
        subject="Coupon Update",
        message=f"Your coupon balance has been updated. You now have {subscription.remaining_coupons} remaining coupons.",
        menu_items=None
    )

    # 5. Redirect back
    return redirect('provider_student_detail', student_id=subscription.student.id)


@login_required
def provider_calendar(request):
    if request.method == "POST":
        selected_dates = request.POST.getlist('dates[]')
        meal_type = request.POST.get('meal_type')
        reason = request.POST.get('reason', '') # Assuming you might add a reason field to the form
        
        if not selected_dates:
            messages.error(request, "Please select at least one date for the holiday.")
            return redirect('provider_calendar')

        try:
            with transaction.atomic():
                for date_str in selected_dates:
                    # Create the holiday entry for each selected date
                    MessHoliday.objects.create(
                        provider=request.user,
                        date=date_str,
                        meal_type=meal_type,
                        reason=reason
                    )

                # Find all active students and send a notification
                active_students = ActiveSubscription.objects.filter(
                    mess_plan__provider=request.user,
                    is_active=True
                )
                
                # Format the dates for the notification message
                dates_str = ', '.join([datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%B %d, %Y') for d in selected_dates])
                
                # Create the notification message
                message = f"Holiday Alert! Your mess, '{request.user.provider_profile.mess_name}', will be closed on the following dates: {dates_str} for {MessHoliday.MealType(meal_type).label}."
                if reason:
                    message += f" Reason: {reason}"
                
                for sub in active_students:
                    Notification.objects.create(
                        recipient=sub.student_profile.user,
                        message=message
                    )

            messages.success(request, "Holidays have been successfully added and students have been notified.")
            return redirect('provider_calendar')

        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
            return redirect('provider_calendar')
    
    # GET request: Display the form and holiday history
    holidays = MessHoliday.objects.filter(provider=request.user).order_by('date')
    context = {
        "holidays": holidays,
    }
    return render(request, "provider/calendar.html", context)

@login_required
def delete_holiday(request, pk):
    """
    Allows a provider to delete a scheduled holiday and notifies students.
    Prevents deletion on or after the holiday date.
    """
    if request.method == "POST":
        try:
            with transaction.atomic():
                # Get the holiday and ensure it belongs to the provider
                holiday = get_object_or_404(MessHoliday, pk=pk, provider=request.user)
                
                # Check if the holiday date is in the past or is today
                if holiday.date <= date.today():
                    messages.error(request, "❌ You cannot delete a holiday on or after its scheduled date.")
                    return redirect('provider_calendar')
                
                # Find all active students to send a notification
                active_students = ActiveSubscription.objects.filter(
                    mess_plan__provider=request.user,
                    is_active=True
                )
                
                # Create and save a notification for each active student
                message = f"Holiday Cancellation Alert! The previously scheduled holiday for your mess '{request.user.provider_profile.mess_name}' on {holiday.date.strftime('%B %d, %Y')} has been cancelled."
                
                for sub in active_students:
                    Notification.objects.create(
                        recipient=sub.student_profile.user,
                        message=message
                    )
                
                # Now, safely delete the holiday
                holiday.delete()
                messages.success(request, "✅ Holiday successfully deleted and students have been notified of the cancellation.")
                
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")

    return redirect('provider_calendar') 

@login_required
def provider_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

     # Mark all unread notifications as read after viewing
    unread_notifications = notifications.filter(is_read=False)
    unread_notifications.update(is_read=True)
    return render(request, 'provider/notifications.html', {'notifications': notifications})


def _send_notifications_to_subscribed_students(provider, subject, message, menu_items=None):
    """Find all active subscribers and send them a notification."""

    # Get all active subscriptions for this provider
    active_subs = ActiveSubscription.objects.filter(
        provider=provider,
        is_active=True
    ).select_related('student_profile__user')

    # Format the message
    messages = message
    if menu_items:
        menu_list = ", ".join([item.dish_name for item in menu_items])
        messages += f" Today's menu is: {menu_list}."

    # Use a set to avoid duplicate user notifications
    notified_users = set()

    for sub in active_subs:
        user = sub.student_profile.user
        if user not in notified_users:
            Notification.objects.create(recipient=user, message=messages, subject=subject)
            notified_users.add(user)

@require_POST
@login_required
def start_mess(request, meal_type):
    """Starts the mess for a specific meal, making it scannable."""
    mess_status, created = MessStatus.objects.get_or_create(
        provider=request.user,
        date=timezone.now().date(),
        meal_type=meal_type.upper()
    )
    # menu_items=MenuItem.objects.filter(id=item_id,provider=request.user)
    if not mess_status.is_active:
        menu_item_ids = request.POST.getlist('menu_items')
        if not menu_item_ids:
            messages.error(request, "Please select at least one menu item.")
            return redirect('provider_home')

        mess_status.is_active = True
        mess_status.started_at = timezone.now()
        mess_status.menu_today.set(MenuItem.objects.filter(id__in=menu_item_ids))
        mess_status.save()
        messages.success(request, f"{meal_type.title()} mess started successfully!")
        _send_notifications_to_subscribed_students(
            provider=request.user,
            subject=f"{meal_type.title()} mess has started!",
            message=f"",
            menu_items=mess_status.menu_today.all()
        )
    else:
        messages.warning(request, f"{meal_type.title()} mess is already active.")
    
    return redirect('provider_home')

# We will create the auto-absent logic in a separate services file later
from .services import mark_absent_students 

@require_POST
@login_required
def stop_mess(request, meal_type):
    """Stops the mess and triggers the auto-absent marking logic."""
    today = timezone.now().date()
    meal_type_upper = meal_type.upper()
    
    mess_status = get_object_or_404(
        MessStatus,
        provider=request.user,
        date=today,
        meal_type=meal_type_upper
    )
    
    if mess_status.is_active:
        mess_status.is_active = False
        mess_status.stopped_at = timezone.now()
        mess_status.save()

        print(request.user,today,meal_type_upper," inside if")
        # --- TRIGGER AUTO-ABSENT LOGIC (Corrected Call) ---
        # We now pass the 'request' object as the first argument
        absent_count = mark_absent_students(
            # request=request,  # <-- THIS IS THE FIX
            provider=request.user.id, 
            date=today, 
            meal_type=meal_type_upper
        )
        students_on_holiday=mark_student_personal_holiday(request.user.id, today, meal_type_upper)
        _send_notifications_to_subscribed_students(
            provider=request.user.id,
            subject=f"{meal_type.title()} Mess Closed",
            message=f"{meal_type.title()} mess has been stopped for {today} at {timezone.now().time()}.",
            menu_items=None
        )
        
        messages.warning(request, f"{meal_type.title()} mess stopped. {absent_count} student(s) marked absent and {students_on_holiday} no. of students are on holiday.")
    else:
        messages.info(request, "Mess was already stopped.")

    return redirect('provider_home')


from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .forms import DailyMenuForm
from django.db import IntegrityError
class ProviderRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'PROVIDER'

class DailyMenuListView(LoginRequiredMixin, ProviderRequiredMixin, ListView):
    model = DailyMenu
    template_name = 'provider/daily_menu_list.html'
    context_object_name = 'menus'
    def get_queryset(self):
        return DailyMenu.objects.filter(provider=self.request.user).order_by('-date')

class DailyMenuCreateView(LoginRequiredMixin, ProviderRequiredMixin, CreateView):
    model = DailyMenu
    form_class = DailyMenuForm
    template_name = 'provider/daily_menu_form.html'
    success_url = reverse_lazy('daily_menu_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['provider'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.provider = self.request.user
        try:
            response = super().form_valid(form)
            messages.success(
                self.request,
                f"✅ Schedule for {form.instance.meal_type} on {form.instance.date} has been set successfully."
            )
            return response
        except IntegrityError:
            messages.error(
                self.request,
                "❌ A menu for this date and meal type already exists."
            )
            return redirect('daily_menu_list')

class DailyMenuUpdateView(LoginRequiredMixin, ProviderRequiredMixin, UpdateView):
    model = DailyMenu
    form_class = DailyMenuForm
    template_name = 'provider/daily_menu_form.html'
    success_url = reverse_lazy('daily_menu_list')
    def get_queryset(self):
        return DailyMenu.objects.filter(provider=self.request.user)
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['provider'] = self.request.user
        return kwargs

class DailyMenuDeleteView(LoginRequiredMixin, ProviderRequiredMixin, DeleteView):
    model = DailyMenu
    template_name = 'provider/daily_menu_confirm_delete.html'
    success_url = reverse_lazy('daily_menu_list')
    def get_queryset(self):
        return DailyMenu.objects.filter(provider=self.request.user)


from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import calendar
import json

# Helper function to get days of the week for grouping
def get_day_of_week_name(day_index):
    # Mapping for SQLite: 0=Sunday, 1=Monday, ...
    return calendar.day_name[day_index]

class ProviderDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'provider/dashboard.html'

    def test_func(self):
        # Ensure only Mess Providers can access this dashboard
        return self.request.user.role == 'PROVIDER'

    def get_context_data(self, request, provider):
        
        # --- 1. KEY METRICS CALCULATION ---
        today = timezone.now().date()
        # today = datetime.date(2025, 10, 15)
        yesterday = today - timedelta(days=1)
        # print(yesterday,today)
        # yesterday = datetime.date(2025, 10, 14)   
        
        active_subscriptions = ActiveSubscription.objects.filter(provider=provider, is_active=True)
        total_active_students = active_subscriptions.count()
        
        # Get list of student IDs who are actively subscribed to this provider
        active_student_ids = active_subscriptions.values_list('student_id', flat=True)
        
        # FIX: Use 'student__in' and the list of active student IDs instead of the broken 'subscription__' lookup
        students_on_holiday_today = StudentHoliday.objects.filter(
            student__in=active_student_ids,
            date=today,
            meal_type__in=['lunch', 'dinner', 'both'] 
        ).values('student').distinct().count()

        expected_attendance_today = total_active_students - students_on_holiday_today

        # Yesterday's meals consumed
        meals_consumed_yesterday = Attendance.objects.filter(
            provider=provider, 
            date=yesterday, 
            status=Attendance.Status.PRESENT
        ).count()
        
        key_metrics = {
            'total_active_students': total_active_students,
            'expected_attendance_today': expected_attendance_today,
            'meals_consumed_yesterday': meals_consumed_yesterday,
        }
        
        # --- 2. DAILY ATTENDANCE TREND (Last 4 Weeks by Day of Week) ---
        four_weeks_ago = today - timedelta(weeks=4)
        total_weeks = 4
        
        # FIX FOR VALUE ERROR: Escaping the '%' sign for SQLite's strftime using '%%'
        attendance_by_day = Attendance.objects.filter(
            provider=provider,
            date__gte=four_weeks_ago,
            status=Attendance.Status.PRESENT,
            # meal_type__in=['lunch', 'dinner']
        ).extra({'day_of_week': "strftime('%%w', date)"}).values('day_of_week', 'meal_type').annotate(
            total_present=Count('id')
        )
        
        # Mapping for SQLite's strftime('%%w'): 0=Sunday, 1=Monday, ..., 6=Saturday
        days_of_week_map = {
            0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday',
            4: 'Thursday', 5: 'Friday', 6: 'Saturday'
        }
        # Desired output order (start with Monday)
        ordered_day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        lunch_data_map = {day: 0 for day in ordered_day_names}
        dinner_data_map = {day: 0 for day in ordered_day_names}
        
        for item in attendance_by_day:
            try:
                day_index = int(item['day_of_week'])
            except (ValueError, TypeError):
                continue
            
            day_name = days_of_week_map.get(day_index)
            
            if day_name and day_name in ordered_day_names:
                average_present = round(item['total_present'] / total_weeks) 
                
                if item['meal_type'] == 'LUNCH':
                    lunch_data_map[day_name] = average_present
                elif item['meal_type'] == 'DINNER':
                    dinner_data_map[day_name] = average_present

        daily_trend_data = {
            'labels': ordered_day_names,
            'lunch_data': [lunch_data_map[day] for day in ordered_day_names],
            'dinner_data': [dinner_data_map[day] for day in ordered_day_names],
        }
        # 🛑 DEBUG STEP 1: Print the raw query results 🛑
        # print("ATTENDANCE TREND RAW DATA:", list(attendance_by_day))

        # ... (rest of the processing loop)

        # 🛑 DEBUG STEP 2: Print the final processed data 🛑
        # print("ATTENDANCE TREND FINAL LUNCH MAP:", lunch_data_map)
        # print("ATTENDANCE TREND FINAL DINNER MAP:", dinner_data_map)

        # --- 3. SUBSCRIPTION & COUPON STATUS (Renewal Forecast) ---
        coupons_data = active_subscriptions.aggregate(
            low=Count('id', filter=Q(remaining_coupons__lte=5)),
            medium=Count('id', filter=Q(remaining_coupons__gt=5, remaining_coupons__lte=15)),
            high=Count('id', filter=Q(remaining_coupons__gt=15)),
        )

        coupon_forecast_data = {
            'labels': ['0-5 (Renew Soon)', '6-15 (Monitor)', '16+ (Stable)'],
            'data': [coupons_data['low'], coupons_data['medium'], coupons_data['high']],
        }

        # --- 4. HOLIDAY/LEAVE IMPACT (Next 7 Days) ---
        next_seven_days = [today + timedelta(days=i) for i in range(1, 8)]
        
        holiday_data = []
        for d in next_seven_days:
            # Filter by student__in(active_student_ids) using the existing schema
            leaves_count = StudentHoliday.objects.filter(
                student__in=active_student_ids,
                date=d
            ).values('student').distinct().count()
            holiday_data.append(leaves_count)

        leave_impact_data = {
            'labels': [d.strftime("%a %d") for d in next_seven_days],
            'leaves': holiday_data,
        }

        # --- 5. MEAL-TIME TRAFFIC VISUALIZATION (Placeholder/Sample) ---
        traffic_labels = ['12:00-1:00', '1:00-2:00', '2:00-3:00', '7:00-8:00', '8:00-9:00', '9:00-10:00']
        traffic_data = [45, 120, 60, 30, 90, 40] 
        
        meal_time_data = {
            'labels': traffic_labels,
            'data': traffic_data,
        }

        context = {
            'key_metrics': key_metrics,
            'daily_trend_data_json': json.dumps(daily_trend_data),
            'coupon_forecast_data_json': json.dumps(coupon_forecast_data),
            'leave_impact_data_json': json.dumps(leave_impact_data),
            'meal_time_data_json': json.dumps(meal_time_data),
        }
        return context


    def get(self, request, *args, **kwargs):
        provider = request.user
        context = self.get_context_data(request, provider)
        return render(request, self.template_name, context)