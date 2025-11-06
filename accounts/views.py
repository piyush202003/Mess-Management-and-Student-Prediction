from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from .models import User, StudentProfile, MessProviderProfile, OTPCode
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from provider.views import provider_home
from student.views import student_home
from django.contrib.auth import logout
from django.utils import timezone # For OTP expiry
import qrcode
import os
import random # For OTP generation
from django.conf import settings
from django.db import transaction # For atomic creation
import re # Added for phone number validation
from django.core.mail import send_mail
from .models import EmailOTP

# Attempt to import Twilio for real SMS sending. If not available, we use simulation.
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False


# Constants
OTP_LENGTH = 6
OTP_VALIDITY_MINUTES = 5

def generate_otp_code():
    """Generates a random 6-digit OTP."""
    # This simulates a secure, randomly generated code
    return str(random.randint(100000, 999999))

def is_valid_phone(phone):
    """Checks if the phone number is a valid 10-digit number."""
    # This regex ensures the phone number is exactly 10 digits and contains only digits.
    # Note: For real international SMS, you would need to accept country codes (e.g., +91xxxxxxxxxx).
    return re.fullmatch(r'\d{10}', phone) is not None

def send_otp_via_sms(phone, otp_code):
    """
    Attempts to send the OTP code via Twilio. Falls back to console print if Twilio is unavailable.
    """
    if TWILIO_AVAILABLE:
        try:
            # Twilio credentials must be configured in settings.py
            account_sid = settings.TWILIO_ACCOUNT_SID
            auth_token = settings.TWILIO_AUTH_TOKEN
            twilio_number = settings.TWILIO_PHONE_NUMBER
            
            client = Client(account_sid, auth_token)
            
            # Note: For production, ensure 'phone' is correctly formatted with country code (e.g., '+91' + phone)
            message = client.messages.create(
                to=f"+91{phone}", # Assuming Indian numbers and prepending +91 for Twilio API
                from_=twilio_number,
                body=f"Your MessApp verification code is: {otp_code}"
            )
            print(f"--- REAL SMS SENT via Twilio (SID: {message.sid}) ---")
            return True
            
        except Exception as e:
            # Log the real Twilio error but fall back to the console print for testing flow
            print(f"--- TWILIO SENDING ERROR: {e} ---")
            print("--- Falling back to console simulation ---")
            
    # Fallback/Simulation for Development or if Twilio fails
    print(f"--- SIMULATED SMS SENDING ---")
    print(f"--- To phone {phone}: Your verification code is {otp_code} ---")
    print(f"-----------------------------")
    return True

def select_role(request):
    return render(request, "accounts/select_role.html")

def student_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and user.role == User.Role.STUDENT:
            login(request, user)
            return redirect("student_home")
        else:
            messages.error(request, "Invalid credentials or not a student account.")
    return render(request, "accounts/student_login.html")

def provider_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user and user.role == User.Role.PROVIDER:
            login(request, user)
            return redirect("provider_home")
        else:
            messages.error(request, "Invalid credentials or not a mess provider account.")
    return render(request, "accounts/provider_login.html")

def student_signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not is_valid_phone(phone):
            messages.error(request, "Please enter a valid 10-digit phone number.")
            return render(request, "accounts/provider_signup.html", request.POST)

        # Validate inputs
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "accounts/student_signup.html")
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "This phone number already exists.")
            return render(request, "accounts/provider_signup.html", request.POST)
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, "accounts/student_signup.html")

        # Store signup data in session temporarily
        request.session['signup_data'] = {
            'username': username,
            'phone' : phone,
            'email': email,
            'password': password,
            'role': User.Role.STUDENT
        }

        # Generate and save OTP
        otp_code = generate_otp_code()
        EmailOTP.objects.filter(email=email).delete()
        EmailOTP.objects.create(email=email, code=otp_code)

        # Send OTP via email
        if send_otp_via_email(email, otp_code):
            messages.success(request, "An OTP has been sent to your email. Please verify to continue.")
            return redirect("email_otp_verification")

        messages.error(request, "Failed to send OTP. Try again later.")
    return render(request, "accounts/student_signup.html")


def provider_signup(request):
    if request.method == "POST":
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        password = request.POST.get("password")

        # 1. New: Phone number format validation
        if not is_valid_phone(phone):
            messages.error(request, "Please enter a valid 10-digit phone number.")
            return render(request, "accounts/provider_signup.html", request.POST)

        # 2. Validation Checks
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, "accounts/provider_signup.html", request.POST)
        if User.objects.filter(phone=phone).exists():
            messages.error(request, "This phone number already exists.")
            return render(request, "accounts/provider_signup.html", request.POST)
        if User.objects.filter(email=email).exists():
            messages.error(request, "This email is already registered.")
            return render(request, "accounts/student_signup.html")

        # 3. Store signup data in session for multi-step process
        request.session['signup_data'] = {
            'username': username,
            'phone': phone,
            'email' : email,
            'password': password,
            'role': User.Role.PROVIDER
        }
        
        # 4. Generate and Save OTP
        # Generate and save OTP
        otp_code = generate_otp_code()
        EmailOTP.objects.filter(email=email).delete()
        EmailOTP.objects.create(email=email, code=otp_code)

        # Send OTP via email
        if send_otp_via_email(email, otp_code):
            messages.success(request, "An OTP has been sent to your email. Please verify to continue.")
            return redirect("email_otp_verification")

        messages.error(request, "Failed to send OTP. Try again later.")
        
    return render(request, "accounts/provider_signup.html")

def otp_verification(request):
    """Handles OTP verification and final account creation."""
    signup_data = request.session.get('signup_data')

    if not signup_data:
        messages.error(request, "Signup data expired or missing. Please start over.")
        return redirect("select_role")

    phone = signup_data['phone']

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')
        
        try:
            # Check for existing OTP for this phone
            otp_obj = OTPCode.objects.get(phone=phone)
        except OTPCode.DoesNotExist:
            messages.error(request, "OTP expired or was never sent. Please resend or try again.")
            return render(request, "accounts/otp_verification.html", {'phone': phone})

        if not otp_obj.is_valid():
            messages.error(request, f"OTP has expired (>{OTP_VALIDITY_MINUTES} mins). Please request a new one.")
            otp_obj.delete()
            return render(request, "accounts/otp_verification.html", {'phone': phone})

        if otp_entered == otp_obj.code:
            # OTP is valid, proceed with user creation
            
            username = signup_data['username']
            password = signup_data['password']
            role = signup_data['role']
            
            try:
                with transaction.atomic():
                    # 1. Create User
                    user = User.objects.create(
                        username=username,
                        phone=phone,
                        # Password must be hashed before saving
                        password=make_password(password), 
                        role=role,
                        is_phone_verified=True # Set verification status
                    )
                    
                    # 2. Create Profile
                    if role == User.Role.STUDENT:
                        StudentProfile.objects.create(user=user, phone_no=phone)
                        redirect_name = "student_login"
                    
                    elif role == User.Role.PROVIDER:
                        # QR Code Generation for Provider
                        qr_data = f"provider_id:{user.id}"
                        qr_img = qrcode.make(qr_data)
                        qr_relative_dir = os.path.join('providers', f'user_{user.id}', 'mess_qr')
                        qr_filename = 'mess_qr.png'
                        qr_abs_dir = os.path.join(settings.MEDIA_ROOT, qr_relative_dir)
                        qr_abs_path = os.path.join(qr_abs_dir, qr_filename)
                        os.makedirs(qr_abs_dir, exist_ok=True)
                        qr_img.save(qr_abs_path)
                        qr_db_path = os.path.join(qr_relative_dir, qr_filename)

                        MessProviderProfile.objects.create(
                            user=user,
                            mess_photo="providers/default.jpg", 
                            mess_qr=qr_db_path,
                            phone_no=phone,
                        )
                        redirect_name = "provider_login"

                    # 3. Clean up OTP and Session
                    otp_obj.delete()
                    del request.session['signup_data']
                    
                    messages.success(request, f"{role.capitalize()} account created and phone verified successfully. Please log in.")
                    return redirect(redirect_name)

            except Exception as e:
                messages.error(request, f"An error occurred during account creation: {e}")
                return render(request, "accounts/otp_verification.html", {'phone': phone})
        
        else:
            messages.error(request, "Invalid OTP.")
            return render(request, "accounts/otp_verification.html", {'phone': phone})

    return render(request, "accounts/otp_verification.html", {'phone': phone})


def custom_logout(request):
    if request.user.is_authenticated:
        role = request.user.role
        logout(request)
        if role == "STUDENT":
            return redirect("student_login")
        elif role == "PROVIDER":
            return redirect("provider_login")
    return redirect("select_role")

def send_otp_via_email(email, otp_code):
    """
    Sends OTP to user's email for verification.
    """
    try:
        subject = "Your Email Verification Code"
        message = f"Your verification code for MessLog is: {otp_code}\nIt will expire in 5 minutes."
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
        print(f"✅ Email OTP sent to {email}: {otp_code}")
        return True
    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False
    
def email_otp_verification(request):
    """Handles OTP verification and account creation."""
    signup_data = request.session.get('signup_data')
    print(signup_data)
    if not signup_data:
        messages.error(request, "Signup data missing. Please start again.")
        return redirect("select_role")

    email = signup_data['email']

    if request.method == 'POST':
        otp_entered = request.POST.get('otp')

        try:
            otp_obj = EmailOTP.objects.get(email=email)
        except EmailOTP.DoesNotExist:
            messages.error(request, "OTP expired or invalid. Please resend or restart signup.")
            return render(request, "accounts/email_otp_verification.html", {'email': email})

        if not otp_obj.is_valid():
            otp_obj.delete()
            messages.error(request, "OTP expired. Please request a new one.")
            return render(request, "accounts/email_otp_verification.html", {'email': email})

        if otp_obj.code == otp_entered:
            # Create and verify user
            with transaction.atomic():
                user = User.objects.create(
                    username=signup_data['username'],
                    phone=signup_data['phone'],
                    email=email,
                    password=make_password(signup_data['password']),
                    role=signup_data['role'],
                    is_email_verified=True
                )

                if signup_data['role'] == User.Role.STUDENT:
                    StudentProfile.objects.create(user=user, email=email)
                    redirect_to = "student_login"
                else:
                    MessProviderProfile.objects.create(user=user, email=email)
                    redirect_to = "provider_login"

                otp_obj.delete()
                del request.session['signup_data']

                messages.success(request, "Email verified and account created successfully.")
                return redirect(redirect_to)

        messages.error(request, "Invalid OTP entered.")
    return render(request, "accounts/email_otp_verification.html", {'email': email})

