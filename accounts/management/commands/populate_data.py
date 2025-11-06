import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# Import your models from all relevant apps
from accounts.models import User, StudentProfile, MessProviderProfile
from provider.models import MessPlan, MenuItem, DailyMenu, MessHoliday
from student.models import ActiveSubscription, Attendance

# --- Configuration ---
# You can adjust these values to change the generated data.
NUM_STUDENTS = 250
DAYS_TO_GENERATE = 30
BASE_ATTENDANCE_PROBABILITY = 0.85 # Base chance a student will attend

# --- Data Definitions ---
VEG_DISHES = [
    "Paneer Butter Masala", "Dal Tadka", "Veg Korma", "Chole Bhature",
    "Aloo Gobi", "Rajma Chawal", "Poha", "Idli Sambhar", "Veg Pulao"
]
NON_VEG_DISHES = [
    "Chicken Curry", "Egg Curry", "Fish Fry", "Chicken Biryani"
]
SPECIAL_DISHES = [
    "Special Veg Thali", "Special Chicken Thali", "Gulab Jamun Special", "Paneer Tikka"
]
HOLIDAYS = {
    (date.today() - timedelta(days=15)): "Local Festival",
    (date.today() - timedelta(days=25)): "Mid-term Break",
}

class Command(BaseCommand):
    help = 'Generates fake data for the mess application for the last 30 days.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Starting data generation process...")

        # --- 1. Clean up old data ---
        self.stdout.write("Deleting old data...")
        User.objects.filter(is_superuser=False).delete()
        MessPlan.objects.all().delete()
        MenuItem.objects.all().delete()
        DailyMenu.objects.all().delete()
        MessHoliday.objects.all().delete()
        # Student models are deleted via CASCADE from User

        # --- 2. Create the Mess Provider ---
        self.stdout.write("Creating mess provider...")
        provider, _ = User.objects.get_or_create(
            username='mess_provider',
            defaults={
                'first_name': 'Raju',
                'last_name': 'Kumar',
                'email': 'provider@mess.com',
                'role': User.Role.PROVIDER,
            }
        )
        provider.set_password('mess_provider')
        provider.save()
        MessProviderProfile.objects.get_or_create(
            user=provider,
            defaults={
                'mess_name': 'Campus Cravings',
                'address': '123 College Road, University Town',
                'service_type': 'BOTH',
                'mess_type': 'BOTH'
            }
        )

        # --- 3. Create a library of Menu Items for the provider ---
        self.stdout.write("Creating menu items...")
        menu_items = []
        all_dishes = VEG_DISHES + NON_VEG_DISHES + SPECIAL_DISHES
        for dish_name in all_dishes:
            item, _ = MenuItem.objects.get_or_create(
                provider=provider,
                dish_name=dish_name,
                defaults={
                    'is_special': dish_name in SPECIAL_DISHES
                }
            )
            menu_items.append(item)

        # --- 4. Create Mess Plans ---
        self.stdout.write("Creating mess plans...")
        plans = []
        plan_details = [
            {'name': 'Monthly Veg Lunch', 'type': 'MONTHLY', 'meal': 'LUNCH', 'mess': 'VEG', 'price': 2000, 'coupons': 30},
            {'name': 'Monthly Veg Both', 'type': 'MONTHLY', 'meal': 'BOTH', 'mess': 'VEG', 'price': 3800, 'coupons': 60},
            {'name': 'Monthly Non-Veg Both', 'type': 'MONTHLY', 'meal': 'BOTH', 'mess': 'BOTH', 'price': 4500, 'coupons': 60},
        ]
        for details in plan_details:
            plan, _ = MessPlan.objects.get_or_create(
                provider=provider,
                plan_name=details['name'],
                defaults={
                    'plan_type': details['type'],
                    'meal_type': details['meal'],
                    'mess_type': details['mess'],
                    'price': details['price'],
                    'coupons': details['coupons'],
                }
            )
            plans.append(plan)

        # --- 5. Create Students and Subscriptions ---
        self.stdout.write(f"Creating {NUM_STUDENTS} students...")
        students = []
        for i in range(NUM_STUDENTS):
            username = f'student_{i+1}'
            student, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': f'Student_{i+1}',
                    'email': f'{username}@university.com',
                    'role': User.Role.STUDENT,
                }
            )
            student.set_password(username)
            student.save()
            students.append(student)

            student_profile, _ = StudentProfile.objects.get_or_create(user=student)
            
            # Assign a random plan
            chosen_plan = random.choice(plans)
            ActiveSubscription.objects.create(
                student_profile=student_profile,
                student=student,
                mess_plan=chosen_plan,
                remaining_coupons=chosen_plan.coupons,
                total_coupons=chosen_plan.coupons,
                activation_date=timezone.now() - timedelta(days=random.randint(0, 25))
            )

        # --- 6. Generate Historical Data for the past 30 days ---
        self.stdout.write("Generating historical daily menus and attendance...")
        start_date = date.today() - timedelta(days=DAYS_TO_GENERATE)
        
        for i in range(DAYS_TO_GENERATE):
            current_date = start_date + timedelta(days=i)
            
            # Check for mess holidays
            if current_date in HOLIDAYS:
                MessHoliday.objects.create(provider=provider, date=current_date, meal_type='BOTH', reason=HOLIDAYS[current_date])

            for meal_time in ['LUNCH', 'DINNER']:
                # Skip if it's a holiday
                if current_date in HOLIDAYS:
                    status = Attendance.Status.MESS_HOLIDAY
                else:
                    # Create a daily menu
                    daily_menu = DailyMenu.objects.create(provider=provider, date=current_date, meal_type=meal_time, is_active=False)
                    # Add 3-5 random dishes to the menu
                    daily_menu.menu_items.set(random.sample(menu_items, k=random.randint(3, 5)))
                    status = None # Will be decided per student

                # Generate attendance for each student
                for student in students:
                    subscription = ActiveSubscription.objects.filter(student=student, is_active=True).first()
                    if not subscription:
                        continue # Skip if no active subscription
                    
                    # Determine final status
                    final_status = status
                    if not final_status:
                        # Simple probability model
                        if random.random() < BASE_ATTENDANCE_PROBABILITY and subscription.remaining_coupons > 0:
                            final_status = Attendance.Status.PRESENT
                            subscription.remaining_coupons -= 1
                            subscription.save()
                        else:
                            final_status = Attendance.Status.ABSENT
                    
                    Attendance.objects.create(
                        student=student,
                        mess_plan=subscription.mess_plan,
                        provider=provider, # <-- FIX: Added the provider here
                        date=current_date,
                        meal_type=meal_time,
                        status=final_status
                    )
        
        self.stdout.write(self.style.SUCCESS('Successfully populated the database with fake data!'))

