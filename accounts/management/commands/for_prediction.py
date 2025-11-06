import random
from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from faker import Faker
from accounts.models import User, StudentProfile
from provider.models import MessPlan, MenuItem, MessHoliday
from student.models import Attendance
from django.db import transaction, IntegrityError
from django.core.management.base import BaseCommand
fake = Faker()
class Command(BaseCommand):
    help = 'Populates the entire database with fake data where username and password are the same.'

    @transaction.atomic  # Use a transaction to ensure data integrity
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting full database population process ---'))
        self.stdout.write(self.style.WARNING('For all created users, the password is the same as the username.'))
        def create_fake_data_for_mess(provider_username, past_days=30):
            # Fetch provider user
            provider = User.objects.get(username=provider_username, role=User.Role.PROVIDER)
            
            # Get one MessPlan for the provider
            mess_plan = MessPlan.objects.filter(provider=provider).first()
            if not mess_plan:
                print("No MessPlan found for provider.")
                return
            
            # Sample menu items linked to this provider
            menu_items = list(MenuItem.objects.filter(provider=provider))
            if not menu_items:
                print("No menu items found for provider.")
                return
            
            # Fetch students with active subscriptions for this provider's mess plan
            active_students = User.objects.filter(active_subscriptions__mess_plan=mess_plan, role=User.Role.STUDENT).distinct()
            if not active_students:
                print("No active student subscriptions found.")
                return
            
            # Dates for past 'past_days' days
            today = datetime.now().date()
            start_date = today - timedelta(days=past_days)
            
            # Meals per day
            meals = ['Lunch', 'Dinner']
            
            # Possible dishes by meal type for simulation
            veg_dishes = [m.dish_name for m in menu_items if 'veg' in m.dish_name.lower()]
            nonveg_dishes = [m.dish_name for m in menu_items if 'nonveg' in m.dish_name.lower() or 'chicken' in m.dish_name.lower() or 'biryani' in m.dish_name.lower()]
            special_dishes = [m.dish_name for m in menu_items if m.is_special]
            
            for day_delta in range(past_days):
                current_date = start_date + timedelta(days=day_delta)
                day_of_week = current_date.strftime('%a')
                
                for meal in meals:
                    # Randomly choose if there's a holiday for that meal
                    holiday = random.choice([False]*8 + [True])  # 10% chance of holiday
                    
                    if holiday:
                        # Create a MessHoliday for provider
                        MessHoliday.objects.get_or_create(
                            provider=provider,
                            date=current_date,
                            meal_type=meal.upper(),
                            defaults={'reason': fake.sentence(nb_words=6)}
                        )
                    
                    for student in active_students:
                        # Randomly decide if student attended (attendance probability lower if holiday)
                        if holiday:
                            attended = False
                            status = Attendance.Status.MESS_HOLIDAY
                        else:
                            attended = random.choices([True, False], weights=[0.85, 0.15])[0]
                            status = Attendance.Status.PRESENT if attended else Attendance.Status.ABSENT
                        
                        # Create or update attendance record
                        Attendance.objects.update_or_create(
                            student=student,
                            mess_plan=mess_plan,
                            provider=provider,
                            date=current_date,
                            meal_type=meal.lower(),
                            defaults={'status': status, 'marked_at': make_aware(datetime.now())}
                        )
            print(f"Fake data created for mess provider '{provider_username}' for past {past_days} days.")
