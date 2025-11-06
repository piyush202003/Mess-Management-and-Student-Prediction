import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import pickle
from pathlib import Path
import logging
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import Count, Avg

logger = logging.getLogger(__name__)


def convert_to_json_safe(stats):
    """Convert NumPy types to Python native types for JSON serialization."""
    if not stats:
        return {}
    
    safe_stats = {}
    for key, value in stats.items():
        if isinstance(value, (np.integer, np.int64, np.int32)):
            safe_stats[key] = int(value)
        elif isinstance(value, (np.floating, np.float64, np.float32)):
            safe_stats[key] = float(value)
        elif isinstance(value, (list, tuple)):
            safe_stats[key] = [convert_to_json_safe({'v': v})['v'] if isinstance(v, (np.integer, np.floating)) else v for v in value]
        else:
            safe_stats[key] = value
    
    return safe_stats


class ProviderDishModel:
    """Provider-specific dish recommendation and prediction model."""
    
    def __init__(self, provider_id):
        self.provider_id = provider_id
        self.model_dir = Path(__file__).parent / 'provider_models' / f'provider_{provider_id}'
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = self.model_dir / 'rf_model.pkl'
        self.encoders_path = self.model_dir / 'encoders.pkl'
        self.scaler_path = self.model_dir / 'scaler.pkl'
        self.stats_path = self.model_dir / 'stats.pkl'
        
        self.rf_model = None
        self.encoders = {}
        self.scaler = None
        self.stats = {
            'avg_attendance': 50,
            'min_attendance': 10,
            'max_attendance': 100,
            'total_samples': 0,
            'dish_performance': {},
            'best_dishes': [],
            'worst_dishes': [],
            'day_patterns': {},
            'meal_patterns': {}
        }
        
        self._load_model()
    
    def _load_model(self):
        """Load existing model if available."""
        try:
            if self.model_path.exists():
                with open(self.model_path, 'rb') as f:
                    self.rf_model = pickle.load(f)
                with open(self.encoders_path, 'rb') as f:
                    self.encoders = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                with open(self.stats_path, 'rb') as f:
                    self.stats = pickle.load(f)
                logger.info(f"Model loaded for provider {self.provider_id}")
                return True
        except Exception as e:
            logger.warning(f"Could not load model for provider {self.provider_id}: {e}")
        return False
    
    def train(self, df):
        """Train provider-specific model with enhanced analytics."""
        if df.empty or len(df) < 20:
            raise ValueError("Insufficient data for training. Need at least 20 records.")
        
        logger.info(f"Training model for provider {self.provider_id} with {len(df)} samples")
        
        # Calculate basic statistics
        self.stats = {
            'avg_attendance': float(df['attended_students'].mean()),
            'min_attendance': int(df['attended_students'].min()),
            'max_attendance': int(df['attended_students'].max()),
            'total_samples': int(len(df))
        }
        
        # Analyze dish performance
        self._analyze_dish_performance(df)
        
        # Analyze day patterns
        self._analyze_day_patterns(df)
        
        # Analyze meal patterns
        self._analyze_meal_patterns(df)
        
        # Prepare encoders
        self.encoders = {}
        feature_columns = {
            'day': ['day_of_week'],
            'type': ['dish_type'],
            'holiday': ['holiday'],
            'meal': ['meal_type']
        }
        
        for key, cols in feature_columns.items():
            encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
            encoder.fit(df[cols])
            self.encoders[key] = encoder
        
        # Encode features
        encoded_parts = []
        for key in ['day', 'type', 'holiday', 'meal']:
            encoded = self.encoders[key].transform(df[[self.encoders[key].feature_names_in_[0]]])
            encoded_parts.append(encoded)
        
        X = np.hstack(encoded_parts)
        y = df['attended_students'].values
        
        # Scale target
        self.scaler = StandardScaler()
        y_scaled = self.scaler.fit_transform(y.reshape(-1, 1)).ravel()
        
        # Train Random Forest
        self.rf_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        # Split if enough data
        if len(X) > 50:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y_scaled, test_size=0.2, random_state=42
            )
            self.rf_model.fit(X_train, y_train)
            score = float(self.rf_model.score(X_test, y_test))
            self.stats['model_score'] = score
            logger.info(f"Model R² score: {score:.4f}")
        else:
            self.rf_model.fit(X, y_scaled)
            self.stats['model_score'] = None
        
        # Save model
        self._save_model()
        
        logger.info(f"Model trained successfully for provider {self.provider_id}")
        logger.info(f"Average attendance: {self.stats['avg_attendance']:.1f}")
        
        return True
    
    def _analyze_dish_performance(self, df):
        """Analyze which dishes perform best."""
        # Group by dish_type and calculate average attendance
        if 'dish_name' in df.columns:
            dish_stats = df.groupby('dish_name')['attended_students'].agg(['mean', 'count']).reset_index()
            dish_stats.columns = ['dish_name', 'avg_attendance', 'count']
            dish_stats = dish_stats[dish_stats['count'] >= 3]  # At least 3 occurrences
            dish_stats = dish_stats.sort_values('avg_attendance', ascending=False)
            
            self.stats['dish_performance'] = {
                row['dish_name']: {
                    'avg_attendance': float(row['avg_attendance']),
                    'count': int(row['count'])
                }
                for _, row in dish_stats.iterrows()
            }
            
            # Best and worst performing dishes
            if len(dish_stats) > 0:
                self.stats['best_dishes'] = dish_stats.head(3)['dish_name'].tolist()
                self.stats['worst_dishes'] = dish_stats.tail(3)['dish_name'].tolist()
        
        # By dish type (veg/nonveg)
        type_stats = df.groupby('dish_type')['attended_students'].agg(['mean', 'count']).reset_index()
        self.stats['type_performance'] = {
            row['dish_type']: {
                'avg_attendance': float(row['mean']),
                'count': int(row['count'])
            }
            for _, row in type_stats.iterrows()
        }
    
    def _analyze_day_patterns(self, df):
        """Analyze attendance patterns by day of week."""
        day_stats = df.groupby('day_of_week')['attended_students'].agg(['mean', 'count']).reset_index()
        self.stats['day_patterns'] = {
            row['day_of_week']: {
                'avg_attendance': float(row['mean']),
                'count': int(row['count'])
            }
            for _, row in day_stats.iterrows()
        }
        
        # Best and worst days
        day_stats = day_stats.sort_values('mean', ascending=False)
        if len(day_stats) > 0:
            self.stats['best_days'] = day_stats.head(3)['day_of_week'].tolist()
            self.stats['worst_days'] = day_stats.tail(3)['day_of_week'].tolist()
    
    def _analyze_meal_patterns(self, df):
        """Analyze attendance patterns by meal time."""
        meal_stats = df.groupby('meal_type')['attended_students'].agg(['mean', 'count']).reset_index()
        self.stats['meal_patterns'] = {
            row['meal_type']: {
                'avg_attendance': float(row['mean']),
                'count': int(row['count'])
            }
            for _, row in meal_stats.iterrows()
        }
    
    def _save_model(self):
        """Save model and preprocessors."""
        with open(self.model_path, 'wb') as f:
            pickle.dump(self.rf_model, f)
        with open(self.encoders_path, 'wb') as f:
            pickle.dump(self.encoders, f)
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        with open(self.stats_path, 'wb') as f:
            pickle.dump(self.stats, f)
    
    def predict(self, day_of_week, dish_type, holiday, meal_type):
        """Predict attendance for given parameters."""
        if self.rf_model is None:
            logger.warning(f"No model available for provider {self.provider_id}, using average")
            return int(self.stats['avg_attendance'])
        
        try:
            # Prepare input
            features = {
                'day': pd.DataFrame([[day_of_week]], columns=['day_of_week']),
                'type': pd.DataFrame([[dish_type]], columns=['dish_type']),
                'holiday': pd.DataFrame([[holiday]], columns=['holiday']),
                'meal': pd.DataFrame([[meal_type]], columns=['meal_type'])
            }
            
            # Encode
            encoded_parts = []
            for key in ['day', 'type', 'holiday', 'meal']:
                encoded = self.encoders[key].transform(features[key])
                encoded_parts.append(encoded)
            
            X = np.hstack(encoded_parts)
            
            # Predict
            pred_scaled = self.rf_model.predict(X)[0]
            predicted = self.scaler.inverse_transform([[pred_scaled]])[0][0]
            
            # Clip to reasonable range
            predicted = np.clip(predicted, self.stats['min_attendance'], self.stats['max_attendance'])
            
            return int(round(predicted))
        
        except Exception as e:
            logger.error(f"Prediction error for provider {self.provider_id}: {e}")
            return int(self.stats['avg_attendance'])
    
    def get_recommendations(self, day_of_week, meal_type, holiday='None'):
        """Get top 3 dish recommendations for given parameters."""
        from provider.models import MenuItem
        
        # Get provider's dishes
        dishes = MenuItem.objects.filter(provider_id=self.provider_id)
        
        recommendations = []
        for dish in dishes:
            dish_type = dish.dish_type.lower() if dish.dish_type else 'veg'
            predicted = self.predict(day_of_week, dish_type, holiday, meal_type)
            
            recommendations.append({
                'dish_name': dish.dish_name,
                'dish_type': dish_type,
                'predicted_attendance': predicted,
                'is_special': dish.is_special
            })
        
        # Sort by predicted attendance
        recommendations.sort(key=lambda x: x['predicted_attendance'], reverse=True)
        
        return recommendations[:3]
    
    def get_historical_data_from_db(self):
        """Fetch historical data from database."""
        from student.models import Attendance
        from provider.models import DailyMenu, MessHoliday, MenuItem
        
        # Get last 60 days of data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=60)
        
        # Get attendance records
        attendance_records = Attendance.objects.filter(
            provider_id=self.provider_id,
            date__range=[start_date, end_date],
            status=Attendance.Status.PRESENT
        ).values('date', 'meal_type').annotate(
            attended_students=Count('id')
        )
        
        # Get menu info
        daily_menus = DailyMenu.objects.filter(
            provider_id=self.provider_id,
            date__range=[start_date, end_date]
        ).prefetch_related('menu_items')
        
        menu_lookup = {(menu.date, menu.meal_type.upper()): menu for menu in daily_menus}
        
        data = []
        for record in attendance_records:
            date = record['date']
            meal_type = record['meal_type']
            
            menu = menu_lookup.get((date, meal_type))
            dish_name = None
            dish_type = 'veg'
            
            if menu and menu.menu_items.exists():
                main_dish = menu.menu_items.first()
                dish_name = main_dish.dish_name
                dish_type = main_dish.dish_type.lower() if main_dish.dish_type else 'veg'
            
            # Determine if holiday
            is_holiday = MessHoliday.objects.filter(
                provider_id=self.provider_id,
                date=date,
                meal_type=meal_type
            ).exists()
            
            data.append({
                'day_of_week': date.strftime('%a'),
                'dish_name': dish_name,
                'dish_type': dish_type,
                'holiday': 'Yes' if is_holiday else 'None',
                'meal_type': meal_type.capitalize(),
                'attended_students': record['attended_students']
            })
        
        return pd.DataFrame(data)


# Helper Functions
def train_provider_model(provider_id):
    """Train model for a specific provider."""
    model = ProviderDishModel(provider_id)
    df = model.get_historical_data_from_db()
    
    if df.empty or len(df) < 20:
        raise ValueError(f"Need at least 20 attendance records. Currently have {len(df)}.")
    
    model.train(df)
    return model


def predict_for_provider(provider_id, day_of_week, dish_type, holiday, meal_type):
    """Get prediction for a provider."""
    model = ProviderDishModel(provider_id)
    return model.predict(day_of_week, dish_type, holiday, meal_type)


def get_recommendations_for_provider(provider_id, day_of_week, meal_type, holiday='None'):
    """Get dish recommendations for a provider."""
    model = ProviderDishModel(provider_id)
    return model.get_recommendations(day_of_week, meal_type, holiday)
