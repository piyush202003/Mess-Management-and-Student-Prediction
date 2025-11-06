from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Student, Provider
from provider.models import *


# class StudentSignUpForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = User
#         fields = ('username', 'email')

#         def clean_username(self):
#             username = self.cleaned_data.get('username')
#             if User.objects.filter(username=username).exists():
#                 raise forms.ValidationError("This username is already taken. Please choose another.")
#             return username


#         def save(self, commit=True):
#             user = super().save(commit=False)
#             user.role = User.Role.STUDENT
#             if commit:
#                 user.save()
#                 Student.objects.create(user=user)  # ID auto-generates
#             return user


# class ProviderSignUpForm(UserCreationForm):
#     class Meta(UserCreationForm.Meta):
#         model = User
#         fields = ('username', 'email')

#     def clean_username(self):
#             username = self.cleaned_data.get('username')
#             if User.objects.filter(username=username).exists():
#                 raise forms.ValidationError("This username is already taken. Please choose another.")
#             return username

#     def save(self, commit=True):
#         user = super().save(commit=False)
#         user.role = User.Role.STUDENT
#         if commit:
#             user.save()
#             Student.objects.create(user=user)  # ID auto-generates
#         return user
from .models import SubscriptionRequest, User
from provider.models import MessPlan


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