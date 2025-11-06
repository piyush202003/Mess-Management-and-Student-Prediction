# ... (add this new class)
from django.db import models
from django.utils.translation import gettext_lazy as _

class MealType(models.TextChoices):
    LUNCH = "LUNCH", _("Lunch")
    DINNER = "DINNER", _("Dinner")

class DayOfWeek(models.IntegerChoices):
    MONDAY = 1, _("Monday")
    TUESDAY = 2, _("Tuesday")
    WEDNESDAY = 3, _("Wednesday")
    THURSDAY = 4, _("Thursday")
    FRIDAY = 5, _("Friday")
    SATURDAY = 6, _("Saturday")
    SUNDAY = 7, _("Sunday")