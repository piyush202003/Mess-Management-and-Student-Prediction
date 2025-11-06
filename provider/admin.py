from django.contrib import admin
from .models import MessPlan


# Helper function to display all fields dynamically
def get_all_fields(model):
    return [field.name for field in model._meta.get_fields() if not field.many_to_many and not field.one_to_many]


@admin.register(MessPlan)
class MessPlanAdmin(admin.ModelAdmin):
    list_display = get_all_fields(MessPlan)  # show every field as a column
    search_fields = ("plan_name", "provider__username", "description")  # text search
    list_filter = ("plan_type", "meal_type", "service_type", "mess_type", "created_at")
    raw_id_fields = ("provider",)  # for large datasets (better than dropdown)
    readonly_fields = ("created_at", "updated_at")  # keep timestamps safe
