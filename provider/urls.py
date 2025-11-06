from django.urls import path
from . import views

urlpatterns = [
    path("provider_home/", views.provider_home, name="provider_home"),
    path("profile/", views.provider_profile, name="provider_profile"),
    # path("qr_page/", views.provider_qr_page, name="qr_page"),
    path('provider/plans/', views.provider_plans, name='provider_plans'),
    path('provider/plans/update/<int:pk>/', views.update_plan, name='update_plan'),
    path('provider/plans/delete/<int:pk>/', views.delete_plan, name='delete_plan'),
    path("requests/", views.manage_requests, name="manage_requests"),
    path("requests/<int:request_id>/<str:action>/", views.update_request_status, name="update_request_status"),
    path('provider/menu/', views.menu_list, name='menu_list'),
    path('provider/menu/create/', views.menu_create, name='menu_create'),
    path('provider/menu/<int:pk>/update/', views.menu_update, name='menu_update'),
    path('proivder/menu/<int:pk>/delete/', views.menu_delete, name='menu_delete'),

    path('manage-students/', views.manage_students, name='manage_students'),
    path('subscription/<int:subscription_id>/increase-coupons/', views.increase_student_coupons, name='increase_coupons'),

    path('calendar/', views.provider_calendar, name='provider_calendar'),
    path('delete_holiday/<int:pk>/', views.delete_holiday, name='delete_holiday'),
    path('notification/',views.provider_notifications, name='notification'),
    
    # path('mess/start/<str:meal_type>/', views.start_mess, name='start_mess'), 
    # path('mess/stop/<str:meal_type>/', views.stop_mess, name='stop_mess'),
    # path('mark-absents/<str:meal_type>/', views.mark_absent_students, name='mark_absents'),
    path('qr-code/', views.provider_qr_page, name='provider_qr_page'),
    path('mess/start/<str:meal_type>', views.start_mess, name='start_mess'),
    path('mess/stop/<str:meal_type>/', views.stop_mess, name='stop_mess'),
    path('students/<int:student_id>/', views.provider_student_detail_view, name='provider_student_detail'),

    path('schedule/', views.DailyMenuListView.as_view(), name='daily_menu_list'),
    path('schedule/add/', views.DailyMenuCreateView.as_view(), name='daily_menu_add'),
    path('schedule/<int:pk>/edit/', views.DailyMenuUpdateView.as_view(), name='daily_menu_edit'),
    path('schedule/<int:pk>/delete/', views.DailyMenuDeleteView.as_view(), name='daily_menu_delete'),

    path('dashboard/', views.ProviderDashboardView.as_view(), name='provider_dashboard'),
]
