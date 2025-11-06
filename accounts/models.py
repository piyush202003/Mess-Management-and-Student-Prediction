from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
import os
from django.conf import settings
from smart_selects.db_fields import ChainedForeignKey
from provider.models import MessPlan
from django.utils import timezone

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", _("Student")
        PROVIDER = "PROVIDER", _("Mess Provider")

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )
    phone = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True, null=True, blank=True)
    unique_id = models.CharField(max_length=20, unique=True, editable=False, null=True, blank=True)
    is_email_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.unique_id:
            prefix = "STU" if self.role == self.Role.STUDENT else "PRO"
            self.unique_id = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


def student_profile_photo_path(instance, filename):
    """
    Generates a unique file path for student profile photos.
    The path will be structured as: students/user_<user_id>/<filename>
    """
    # Get the file extension
    ext = filename.split('.')[-1]
    # Construct the filename using the user's ID
    new_filename = f'profile_photo.{ext}'
    # Return the full file path
    return os.path.join('students', f'user_{instance.user.id}', new_filename)

def provider_profile_photo_path(instance, filename):
    """
    Generates a unique file path for mess provider photos.
    The path will be structured as: providers/user_<user_id>/<filename>
    """
    ext = filename.split('.')[-1]
    new_filename = f'mess_photo.{ext}'
    return os.path.join('providers', f'user_{instance.user.id}', new_filename)

def mess_qr_photo_path(instance, filename):
    """
    Generates a unique file path for mess QR codes.
    The path will be structured as: providers/user_<user_id>/mess_qr/<filename>
    """
    ext = filename.split('.')[-1]
    new_filename = f'mess_qr.{ext}'
    return os.path.join('providers', f'user_{instance.user.id}', 'mess_qr', new_filename)

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    full_name = models.CharField(max_length=100, blank=True)
    phone_no = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    dob = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    profile_photo = models.ImageField(upload_to=student_profile_photo_path, null=True, blank=True)
    email = models.EmailField(blank=True,null=True)



class MessProviderProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="provider_profile")
    full_name = models.CharField(max_length=100, blank=True)
    phone_no = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True,null=True)
    service_type = models.CharField(max_length=20, choices=[("DINING", "Dining"), ("TIFINE", "Tiffin"), ("BOTH", "Both")], blank=True)
    mess_type = models.CharField(max_length=20, choices=[("VEG", "Veg"), ("NON-VEG", "Non-Veg"), ("BOTH", "Both")], blank=True)
    address = models.TextField(blank=True)
    lunch_start = models.TimeField(null=True, blank=True)
    lunch_end = models.TimeField(null=True, blank=True)
    dinner_start = models.TimeField(null=True, blank=True)
    dinner_end = models.TimeField(null=True, blank=True)
    mess_photo = models.ImageField(upload_to=provider_profile_photo_path, null=True, blank=True,default="providers/default.jpg")
    mess_name = models.CharField(max_length=100, blank=True)
    mess_qr = models.ImageField(upload_to=mess_qr_photo_path, null=True, blank=True)

class SubscriptionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscription_requests")
    plan = models.ForeignKey('provider.MessPlan', on_delete=models.CASCADE, related_name="subscription_requests")
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_requests")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_requests")
    plan = ChainedForeignKey(
        MessPlan,
        chained_field="provider",
        chained_model_field="provider",
        show_all=False,
        auto_choose=True,
        sort=True,
        related_name="subscription_requests"
    )
    
    def __str__(self):
        return f"Request for {self.plan.plan_name} by {self.student.username}"
    
class OTPCode(models.Model):
    """Model to store temporary OTPs for phone number verification."""
    phone = models.CharField(max_length=15, unique=True, verbose_name="Phone Number")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Checks if the OTP is still valid (e.g., within 5 minutes)."""
        # OTP is valid for 5 minutes (300 seconds)
        return (timezone.now() - self.created_at).total_seconds() < 300

    def __str__(self):
        return f"OTP {self.code} for {self.phone}"
    
class EmailOTP(models.Model):
    """Stores OTPs for email verification."""
    email = models.EmailField(unique=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        """Check if OTP is valid within 5 minutes."""
        return (timezone.now() - self.created_at).total_seconds() < 300

    def __str__(self):
        return f"OTP {self.code} for {self.email}"

