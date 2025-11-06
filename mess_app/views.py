from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .ml.provider_model import (
    ProviderDishModel,
    train_provider_model,
    predict_for_provider,
    get_recommendations_for_provider,
    convert_to_json_safe
)
from .models import PredictionLog, ModelPerformance
from accounts.models import User
from provider.models import MenuItem
from student.models import Attendance
import logging
import traceback

logger = logging.getLogger(__name__)


@login_required
def retrain_model_view(request, provider_id):
    """View to retrain provider's model with detailed error handling."""
    provider = get_object_or_404(User, id=provider_id, role='PROVIDER')
    
    if request.user.id != provider_id and not request.user.is_staff:
        messages.error(request, "You don't have permission to retrain this model.")
        return redirect('provider_dashboard')
    
    if request.method == 'POST':
        try:
            logger.info(f"Starting model retraining for provider {provider_id}")
            
            # Check if we have data
            model = ProviderDishModel(provider_id)
            df = model.get_historical_data_from_db()
            
            logger.info(f"Retrieved {len(df)} records from database")
            
            if df.empty:
                raise ValueError("No attendance data found. Start tracking attendance first.")
            
            if len(df) < 20:
                raise ValueError(f"Need at least 20 attendance records. Currently have {len(df)}.")
            
            # Check data quality
            if 'attended_students' not in df.columns:
                raise ValueError("Data missing 'attended_students' column")
            
            logger.info(f"Data columns: {df.columns.tolist()}")
            logger.info(f"Data shape: {df.shape}")
            logger.info(f"Sample data:\n{df.head()}")
            
            # Train the model
            logger.info("Starting model training...")
            model.train(df)
            logger.info("Model training completed successfully")
            
            # Save performance metrics
            try:
                ModelPerformance.objects.create(
                    provider=provider,
                    training_samples=model.stats['total_samples'],
                    model_score=model.stats.get('model_score')
                )
                logger.info("Performance metrics saved")
            except Exception as e:
                logger.warning(f"Could not save performance metrics: {e}")
            
            # Convert stats to JSON-safe format
            safe_stats = convert_to_json_safe(model.stats)
            
            messages.success(
                request,
                f"✓ Model retrained successfully! "
                f"Trained on {safe_stats['total_samples']} records. "
                f"Average attendance: {safe_stats['avg_attendance']:.1f} students."
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Model retrained successfully',
                    'stats': safe_stats
                })
            
            return redirect('analytics', provider_id=provider_id)
            
        except ValueError as e:
            error_msg = str(e)
            logger.error(f"ValueError during retraining: {error_msg}")
            messages.error(request, f"Cannot retrain model: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            return redirect('provider_dashboard')
        
        except Exception as e:
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            logger.error(f"Error retraining model for provider {provider_id}")
            logger.error(f"Error message: {error_msg}")
            logger.error(f"Stack trace:\n{stack_trace}")
            
            # More specific error message
            if "dish_type" in error_msg.lower():
                messages.error(request, "Error: Issue with dish type data. Please check your menu items have valid dish types.")
            elif "attended_students" in error_msg.lower():
                messages.error(request, "Error: Issue with attendance data. Please verify attendance records are valid.")
            elif "fit" in error_msg.lower():
                messages.error(request, "Error: Model training failed. Your data might have inconsistencies.")
            else:
                messages.error(request, f"An error occurred while retraining: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=500)
            return redirect('provider_dashboard')
    
    # GET request
    try:
        model = ProviderDishModel(provider_id)
        df = model.get_historical_data_from_db()
        
        context = {
            'provider': provider,
            'has_model': model.rf_model is not None,
            'current_stats': convert_to_json_safe(model.stats) if model.rf_model else None,
            'available_records': len(df),
            'min_records_needed': 20,
        }
        
        return render(request, 'mess_app/retrain_confirm.html', context)
    except Exception as e:
        logger.error(f"Error loading retrain page: {e}")
        messages.error(request, "Error loading page. Please try again.")
        return redirect('provider_dashboard')


@login_required
def predict_dish(request, provider_id):
    """Manual dish prediction."""
    provider = get_object_or_404(User, id=provider_id, role='PROVIDER')
    
    if request.user.id != provider_id and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        model = ProviderDishModel(provider_id)
        df = model.get_historical_data_from_db()
        
        provider_menu_items = MenuItem.objects.filter(provider_id=provider_id).order_by('dish_name')
        
        # Handle dish types properly
        dish_types = {}
        for item in provider_menu_items:
            if hasattr(item.dish_type, 'lower'):
                dish_types[item.dish_name] = item.dish_type.lower()
            elif item.dish_type:
                dish_types[item.dish_name] = str(item.dish_type).lower()
            else:
                dish_types[item.dish_name] = 'veg'
        
        context = {
            'provider': provider,
            'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'meals': ['Lunch', 'Dinner'],
            'dishes': [item.dish_name for item in provider_menu_items],
            'dish_types': dish_types,
            'has_model': model.rf_model is not None,
            'model_stats': convert_to_json_safe(model.stats),
            'available_records': len(df),
        }
        
        if request.method == "POST":
            try:
                day = request.POST.get('day')
                holiday = request.POST.get('holiday', 'None').capitalize()
                meal_time = request.POST.get('meal_time')
                selected_dish = request.POST.get('dish')
                
                dish_type = dish_types.get(selected_dish, 'veg')
                
                predicted_attendance = predict_for_provider(
                    provider_id, day, dish_type, holiday, meal_time
                )
                
                context.update({
                    'selected_dish': selected_dish,
                    'predicted_attendance': predicted_attendance,
                    'selected_day': day,
                    'selected_holiday': holiday,
                    'selected_meal_time': meal_time,
                    'prediction_made': True,
                })
                
                messages.success(request, f"Prediction: {predicted_attendance} students expected")
                
            except Exception as e:
                logger.error(f"Prediction error: {e}", exc_info=True)
                messages.error(request, f"Error generating prediction: {str(e)}")
        
        return render(request, 'mess_app/predict.html', context)
    
    except Exception as e:
        logger.error(f"Error in predict_dish: {e}", exc_info=True)
        messages.error(request, "Error loading prediction page.")
        return redirect('provider_dashboard')


@login_required
def recommend_dish(request, provider_id):
    """AI-powered dish recommendation."""
    provider = get_object_or_404(User, id=provider_id, role='PROVIDER')
    
    if request.user.id != provider_id and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        model = ProviderDishModel(provider_id)
        
        context = {
            'provider': provider,
            'days': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'meals': ['Lunch', 'Dinner'],
            'has_model': model.rf_model is not None,
            'model_stats': convert_to_json_safe(model.stats),
        }
        
        if request.method == "POST":
            try:
                day = request.POST.get('day')
                holiday = request.POST.get('holiday', 'None').capitalize()
                meal_time = request.POST.get('meal_time')
                
                # Get recommendations
                recommendations = get_recommendations_for_provider(
                    provider_id, day, meal_time, holiday
                )
                
                context.update({
                    'recommendations': recommendations,
                    'selected_day': day,
                    'selected_holiday': holiday,
                    'selected_meal_time': meal_time,
                    'recommendation_made': True,
                })
                
                if recommendations:
                    messages.success(
                        request,
                        f"Top recommendation: {recommendations[0]['dish_name']} "
                        f"(Expected: {recommendations[0]['predicted_attendance']} students)"
                    )
                
            except Exception as e:
                logger.error(f"Recommendation error: {e}", exc_info=True)
                messages.error(request, f"Error generating recommendations: {str(e)}")
        
        return render(request, 'mess_app/recommend.html', context)
    
    except Exception as e:
        logger.error(f"Error in recommend_dish: {e}", exc_info=True)
        messages.error(request, "Error loading recommendation page.")
        return redirect('provider_dashboard')


@login_required
def analytics_dashboard(request, provider_id):
    """Analytics dashboard with performance metrics."""
    provider = get_object_or_404(User, id=provider_id, role='PROVIDER')
    
    if request.user.id != provider_id and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('home')
    
    try:
        model = ProviderDishModel(provider_id)
        
        # Get recent predictions
        recent_predictions = PredictionLog.objects.filter(
            provider=provider
        ).order_by('-date')[:10]
        
        # Get model performance history
        performance_history = ModelPerformance.objects.filter(
            provider=provider
        ).order_by('-training_date')[:5]
        
        # Calculate accuracy metrics
        predictions_with_actuals = PredictionLog.objects.filter(
            provider=provider,
            actual_attendance__isnull=False
        )
        
        avg_accuracy = None
        if predictions_with_actuals.exists():
            accuracies = [p.accuracy_percentage for p in predictions_with_actuals if p.accuracy_percentage]
            if accuracies:
                avg_accuracy = sum(accuracies) / len(accuracies)
        
        context = {
            'provider': provider,
            'has_model': model.rf_model is not None,
            'model_stats': convert_to_json_safe(model.stats),
            'recent_predictions': recent_predictions,
            'performance_history': performance_history,
            'avg_accuracy': round(avg_accuracy, 2) if avg_accuracy else None,
        }
        
        return render(request, 'mess_app/analytics.html', context)
    
    except Exception as e:
        logger.error(f"Error in analytics_dashboard: {e}", exc_info=True)
        messages.error(request, "Error loading analytics.")
        return redirect('dashboard')


# Debug view to check data
@login_required
def debug_data(request, provider_id):
    """Debug view to check what data is available."""
    if not request.user.is_staff and request.user.id != provider_id:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        from provider.models import DailyMenu, MessHoliday
        
        model = ProviderDishModel(provider_id)
        df = model.get_historical_data_from_db()
        
        # Check attendance records
        attendance_count = Attendance.objects.filter(
            provider_id=provider_id,
            status=Attendance.Status.PRESENT
        ).count()
        
        # Check menu items
        menu_items_count = MenuItem.objects.filter(provider_id=provider_id).count()
        
        # Check daily menus
        daily_menus_count = DailyMenu.objects.filter(provider_id=provider_id).count()
        
        debug_info = {
            'provider_id': provider_id,
            'attendance_records': attendance_count,
            'menu_items': menu_items_count,
            'daily_menus': daily_menus_count,
            'historical_data_rows': len(df),
            'data_columns': df.columns.tolist() if not df.empty else [],
            'sample_data': df.head(5).to_dict('records') if not df.empty else [],
            'data_types': {col: str(dtype) for col, dtype in df.dtypes.items()} if not df.empty else {},
        }
        
        return JsonResponse(debug_info, safe=False)
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
