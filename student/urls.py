from django.urls import path
from . import views

urlpatterns = [
    path("std_home/", views.student_home, name="student_home"),
    path("std_profile/", views.student_profile, name="student_profile"),
    path("std_search/",views.student_search_mess, name="student_search_mess"),
    path('student/provider/<int:provider_pk>/', views.provider_details, name='provider_details'),
    path('student/request_subscription/<int:plan_id>/', views.request_subscription, name='request_subscription'),
    path("subscriptions/", views.my_subscriptions, name="my_subscriptions"),

    # path("complaints/", views.student_complaints, name="student_complaints"),

    path('active_subscriptions/', views.active_subscriptions, name='active_subscriptions'),
    path('menu/<int:provider_id>/', views.view_provider_menu, name='view_provider_menu'),
    path('mess/<int:provider_id>/menu/', views.public_provider_menu, name='public_provider_menu'),
    path('student_holiday/',views.student_holiday, name="student_holiday"),
    path('get_plan_meal_type/<int:plan_id>/', views.get_plan_meal_type, name='get_plan_meal_type'),
    path('notifications/', views.student_notifications, name='student_notifications'),

    # path("scan-qr/<int:provider_id>/", views.scan_qr_attendance, name="scan_qr_attendance"),
    path('scan/<str:provider_unique_id>/', views.student_scan_qr, name='student_scan_qr'),
    path('attendance-history/', views.student_attendance_history, name='student_attendance_history'),
    path('scan-page/', views.student_scan_page_view, name='student_scan_page'),

    
]
