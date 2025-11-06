# from django.db import models
# from django.conf import settings
# from student.models import Subscription


# class MealSession(models.Model):
#     provider = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         limit_choices_to={'role': 'PROVIDER'},
#         related_name="meal_sessions"
#     )
#     meal_type = models.CharField(max_length=10, choices=[("LUNCH", "Lunch"), ("DINNER", "Dinner")])
#     date = models.DateField()
#     start_time = models.DateTimeField(auto_now_add=True)
#     end_time = models.DateTimeField(null=True, blank=True)
#     active = models.BooleanField(default=True)

#     class Meta:
#         unique_together = ("provider", "meal_type", "date")

#     def __str__(self):
#         return f"{self.provider.username} - {self.meal_type} ({self.date})"


# class Attendance(models.Model):
#     subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="attendances")
#     student = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         limit_choices_to={'role': 'STUDENT'},
#         related_name="attendances"
#     )
#     provider = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         limit_choices_to={'role': 'PROVIDER'},
#         related_name="attendances"
#     )
#     session = models.ForeignKey(MealSession, on_delete=models.CASCADE, null=True, blank=True)

#     date = models.DateField()
#     meal_type = models.CharField(max_length=10, choices=[("LUNCH", "Lunch"), ("DINNER", "Dinner")])
#     status = models.CharField(
#         max_length=20,
#         choices=[
#             ("PRESENT", "Present"),
#             ("ABSENT", "Absent"),
#             ("HOLIDAY", "Holiday (Student)"),
#             ("PROVIDER_HOLIDAY", "Holiday (Provider)")
#         ],
#         default="PRESENT"
#     )
#     scan_time = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ("subscription", "date", "meal_type")

#     def __str__(self):
#         return f"{self.student.username} - {self.meal_type} ({self.date}) - {self.status}"


# class StudentHolidayRequest(models.Model):
#     subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="holiday_requests")
#     date = models.DateField()
#     meal_type = models.CharField(max_length=10, choices=[("LUNCH", "Lunch"), ("DINNER", "Dinner")])
#     created_at = models.DateTimeField(auto_now_add=True)
#     approved = models.BooleanField(default=False)

#     class Meta:
#         unique_together = ("subscription", "date", "meal_type")

#     def __str__(self):
#         return f"HolidayRequest {self.subscription.student.username} - {self.date} {self.meal_type}"
