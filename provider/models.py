from django.db import models
import os
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .choices import *

def plan_image_path(instance, filename):
    """
    Generates a unique file path for provider plan images.
    The path will be structured as: providers/user_<user_id>/plans/<filename>
    """
    ext = filename.split('.')[-1]
    new_filename = f'plan_{instance.id or "new"}.{ext}'
    return os.path.join('providers', f'user_{instance.provider.id}', 'plans', new_filename)

def menu_image_path(instance, filename):
    """
    Generates a unique file path for provider menu images.
    The path will be structured as: providers/user_<user_id>/menus/<filename>
    """
    # menu_image = models.ImageField(upload_to=menu_image_path, null=True, blank=True, default="providers/default_menu.jpg")
    ext = filename.split('.')[-1]
    new_filename = f'menu_{instance.id or "new"}.{ext}'
    return os.path.join('providers', f'user_{instance.provider.id}', 'menus', new_filename)


class MessPlan(models.Model):
    class PlanType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        YEARLY = "YEARLY", "Yearly"
        ONE_TIME = "ONE_TIME", "One-Time"

    class MealType(models.TextChoices):
        LUNCH = "LUNCH", "Lunch"
        DINNER = "DINNER", "Dinner"
        BOTH = "BOTH", "Lunch & Dinner"

    class ServiceType(models.TextChoices):
        DINING = "DINING", "Dining"
        TIFFIN = "TIFFIN", "Tiffin"
        BOTH = "BOTH", "Both"

    class MessType(models.TextChoices):
        VEG = "VEG", "Veg"
        NON_VEG = "NON-VEG", "Non-Veg"
        BOTH = "BOTH", "Both"

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        related_name="mess_plans"
    )
    plan_name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PlanType.choices)
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    service_type = models.CharField(max_length=20, choices=ServiceType.choices)
    mess_type = models.CharField(max_length=20, choices=MessType.choices)
    coupons = models.PositiveIntegerField(help_text="Number of meals included")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)
    plan_image = models.ImageField(upload_to=plan_image_path, null=True, blank=True, default="providers/default_plan.jpg")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True, help_text="Check this to make the plan visible to customers.",null=True,blank=True)

    def __str__(self):
        return f"{self.plan_name} ({self.plan_type}) - {self.provider.username}"

class MenuItem(models.Model):
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        related_name="menu_items"
    )
    dish_name = models.CharField(max_length=100)
    dish_description = models.TextField(blank=True)
    dish_image = models.ImageField(upload_to=menu_image_path, null=True, blank=True, default="providers/default_menu.jpg")
    is_special = models.BooleanField(default=False, help_text="Mark this dish as a special item.",null=True,blank=True)
    dish_type = models.CharField(max_length=20, choices=[('veg', 'Veg'), ('nonveg', 'Non-Veg')], default='veg')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('provider', 'dish_name')  # Prevent duplicate dish names per provider

    def __str__(self):
        return f"{self.dish_name} - {self.provider.username}"
    
class MessHoliday(models.Model):
    class MealType(models.TextChoices):
        LUNCH = "LUNCH", _("Lunch")
        DINNER = "DINNER", _("Dinner")
        BOTH = "BOTH", _("Both")

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        related_name="mess_holidays"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'date', 'meal_type')
        ordering = ['date']

    def __str__(self):
        return f"{self.provider.username} holiday on {self.date} for {self.meal_type}"

# notification
class ProviderNotification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="provider_notifications")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}"

# mess start button
class DailyMenu(models.Model):
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        related_name="daily_menus"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MealType.choices)
    
    # This is where the provider will select the dishes for the day
    menu_items = models.ManyToManyField('MenuItem', blank=True, related_name="daily_menus")

    # We can keep these fields if you still want a start/stop feature
    is_active = models.BooleanField(default=False) 
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('provider', 'date', 'meal_type')
        ordering = ['-date', 'meal_type'] # Show most recent first

    def __str__(self):
        return f"{self.provider.username} - {self.date} {self.get_meal_type_display()}"

class MessStatus(models.Model):
    """
    Tracks the real-time status of a provider's mess for a specific meal on a given day.
    """
    class MealType(models.TextChoices):
        LUNCH = "LUNCH", _("Lunch")
        DINNER = "DINNER", _("Dinner")

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'PROVIDER'},
        related_name="mess_status"
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=10, choices=MealType.choices)
    is_active = models.BooleanField(default=False)
    menu_today = models.ManyToManyField(MenuItem, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('provider', 'date', 'meal_type')

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.provider.username} - {self.date} {self.meal_type} - {status}"
