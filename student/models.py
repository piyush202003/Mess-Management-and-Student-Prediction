from django.db import models
from django.conf import settings
from accounts.models import StudentProfile
from provider.models import MessPlan
from django.utils import timezone

class ActiveSubscription(models.Model):
    student_profile = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="active_subscriptions")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'},
        related_name="active_subscriptions",
        null=True, # To allow for data migration
    )
    mess_plan = models.ForeignKey(MessPlan, on_delete=models.CASCADE, related_name="active_subscriptions")
    provider= models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        null=True, # To allow for data migration
        related_name="student_subscriptions"
    )
    activation_date = models.DateTimeField(default=timezone.now)
    remaining_coupons = models.PositiveIntegerField()
    total_coupons = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True) # To easily deactivate subscriptions

    def __str__(self):
        return f"{self.student_profile.user.username} - {self.mess_plan.plan_name}"

    def save(self, *args, **kwargs):
        # Ensure remaining_coupons is not greater than total_coupons
        if self.remaining_coupons > self.total_coupons:
            self.remaining_coupons = self.total_coupons
        super().save(*args, **kwargs)

class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    subject = models.CharField(max_length=255,null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}"

class StudentHoliday(models.Model):
    MEAL_CHOICES = [
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
        ('both', 'Lunch & Dinner'),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'},
        related_name="student_holidays"
    )
    mess_plan = models.ForeignKey(MessPlan, on_delete=models.CASCADE)
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'mess_plan', 'date', 'meal_type')

    def __str__(self):
        return f"{self.student.username} - {self.mess_plan.plan_name} - {self.date} ({self.meal_type})"

class Attendance(models.Model):
    MEAL_CHOICES = [
        ('lunch', 'Lunch'),
        ('dinner', 'Dinner'),
    ]
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        PERSONAL_HOLIDAY = "PERSONAL_HOLIDAY", "On Leave"
        MESS_HOLIDAY = "MESS_HOLIDAY", "Mess Holiday"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'STUDENT'},
        related_name='attendances'
    )
    mess_plan = models.ForeignKey('provider.MessPlan', on_delete=models.CASCADE, related_name="attendances")
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        related_name="student_attendances"
    )
    #related_name='mess_attendances'
    date = models.DateField(default=timezone.now)
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABSENT)
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'mess_plan', 'date', 'meal_type')

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.student.username} - {self.mess_plan.plan_name} - {self.date} ({self.meal_type}) - {status}"

