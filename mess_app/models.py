from django.db import models
from django.conf import settings
from django.utils import timezone


class PredictionLog(models.Model):
    """Log predictions vs actual attendance for tracking accuracy."""
    
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prediction_logs'
    )
    date = models.DateField()
    meal_type = models.CharField(max_length=20)
    dish_name = models.CharField(max_length=100)
    dish_type = models.CharField(max_length=20)
    
    predicted_attendance = models.IntegerField()
    actual_attendance = models.IntegerField(null=True, blank=True)
    
    accuracy_percentage = models.FloatField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['provider', 'date']),
        ]
    
    def __str__(self):
        return f"{self.provider.username} - {self.date} - {self.dish_name}"
    
    def calculate_accuracy(self):
        """Calculate prediction accuracy."""
        if self.actual_attendance is not None:
            diff = abs(self.predicted_attendance - self.actual_attendance)
            accuracy = max(0, 100 - (diff / max(self.actual_attendance, 1) * 100))
            self.accuracy_percentage = round(accuracy, 2)
            self.save()
            return self.accuracy_percentage
        return None


class ModelPerformance(models.Model):
    """Track overall model performance metrics."""
    
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='model_performances'
    )
    
    training_date = models.DateTimeField(default=timezone.now)
    training_samples = models.IntegerField()
    model_score = models.FloatField(null=True, blank=True)
    
    avg_prediction_accuracy = models.FloatField(null=True, blank=True)
    total_predictions = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-training_date']
    
    def __str__(self):
        return f"{self.provider.username} - {self.training_date.date()}"
