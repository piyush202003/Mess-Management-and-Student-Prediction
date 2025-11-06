from django.urls import path
from accounts.views import *
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # path('login/', UserLoginView.as_view(), name='login'),
    # path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    # path('signup/student/', student_signup, name='student_signup'),
    # path('signup/provider/', provider_signup, name='provider_signup'),
    path("select-role/", select_role, name="select_role"),
    path("student/login/", student_login, name="student_login"),
    path("provider/login/", provider_login, name="provider_login"),
    path("student/signup/", student_signup, name="student_signup"),
    path("provider/signup/", provider_signup, name="provider_signup"),
    path("logout/", custom_logout, name="logout"),
    path('verify-otp/', otp_verification, name='otp_verification'),
    path("email-otp-verification/", email_otp_verification, name="email_otp_verification"),


]
