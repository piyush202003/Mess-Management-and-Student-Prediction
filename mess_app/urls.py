from django.urls import path
from . import views

urlpatterns = [
    # Prediction & Recommendation
    path('predict/<int:provider_id>/', views.predict_dish, name='predict_dish'),
    path('recommend/<int:provider_id>/', views.recommend_dish, name='recommend_dish'),
    
    # Model Management
    path('retrain/<int:provider_id>/', views.retrain_model_view, name='retrain_model'),
    
    # Analytics & Performance
    path('analytics/<int:provider_id>/', views.analytics_dashboard, name='analytics'),

    path('debug/<int:provider_id>/', views.debug_data, name='debug_data'),
]
