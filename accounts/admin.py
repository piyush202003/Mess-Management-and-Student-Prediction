from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudentProfile, MessProviderProfile
from django import forms
from .models import *
from provider.models import MessPlan


# Helper to display all fields automatically
def get_all_fields(model):
    return [field.name for field in model._meta.get_fields() if not field.many_to_many and not field.one_to_many]


# --- Custom User Admin ---
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = get_all_fields(User)  # show ALL fields
    search_fields = get_all_fields(User)
    list_filter = ("role", "is_active", "is_staff")


# --- Student Profile Admin ---
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone_no", "gender", "dob")
    search_fields = ("full_name", "phone_no", "user__username")
    list_filter = ("gender",)
    raw_id_fields = ("user",)

    # restrict user dropdown to students only
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(role=User.Role.STUDENT)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# --- Mess Provider Profile Admin ---
@admin.register(MessProviderProfile)
class MessProviderProfileAdmin(admin.ModelAdmin):
    list_display = get_all_fields(MessProviderProfile)
    search_fields = get_all_fields(MessProviderProfile)


# --- Subscription Request Admin ---
class SubscriptionRequestForm(forms.ModelForm):
    class Meta:
        model = SubscriptionRequest
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # only students
        self.fields["student"].queryset = User.objects.filter(role=User.Role.STUDENT)

        # only providers
        self.fields["provider"].queryset = User.objects.filter(role=User.Role.PROVIDER)

        # filter plans (if provider already selected)
        if "provider" in self.data:  # when creating in admin
            try:
                provider_id = int(self.data.get("provider"))
                self.fields["plan"].queryset = MessPlan.objects.filter(provider_id=provider_id)
            except (ValueError, TypeError):
                self.fields["plan"].queryset = MessPlan.objects.none()
        elif self.instance.pk:  # when editing an existing request
            self.fields["plan"].queryset = MessPlan.objects.filter(provider=self.instance.provider)
        else:
            self.fields["plan"].queryset = MessPlan.objects.none()
            

