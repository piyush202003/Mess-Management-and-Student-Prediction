import random
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction, IntegrityError
from faker import Faker

# --- Import all your models from all three apps ---
from accounts.models import User, StudentProfile, MessProviderProfile, SubscriptionRequest
from provider.models import MessPlan, MenuItem, MessHoliday, ProviderNotification
from student.models import ActiveSubscription, StudentHoliday
# Alias StudentNotification to avoid name conflict with ProviderNotification
from student.models import Notification as StudentNotification

class Command(BaseCommand):
    help = 'Populates the entire database with fake data where username and password are the same.'

    @transaction.atomic  # Use a transaction to ensure data integrity
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('--- Starting full database population process ---'))
        self.stdout.write(self.style.WARNING('For all created users, the password is the same as the username.'))


        # 0. Initialize Faker
        fake = Faker('en_IN')

        # 1. Clear existing data
        self.stdout.write('Clearing old data...')
        StudentHoliday.objects.all().delete()
        ActiveSubscription.objects.all().delete()
        StudentNotification.objects.all().delete()
        SubscriptionRequest.objects.all().delete()
        MessHoliday.objects.all().delete()
        MenuItem.objects.all().delete()
        ProviderNotification.objects.all().delete()
        MessPlan.objects.all().delete()
        StudentProfile.objects.all().delete()
        MessProviderProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('Old data cleared successfully.'))

        # 2. Create Users and Profiles
        students = []
        providers = []

        self.stdout.write('Creating student users and profiles...')
        for i in range(30):
            # *** MODIFICATION HERE ***
            # Generate username and use it for the password as well
            username = fake.unique.user_name()
            
            user = User.objects.create_user(
                username=username,
                email=fake.email(),
                password=username, # Set password same as username
                role=User.Role.STUDENT,
                phone=fake.phone_number()[:15]
            )
            StudentProfile.objects.create(
                user=user, full_name=fake.name(), phone_no=user.phone,
                gender=random.choice(['Male', 'Female']), dob=fake.date_of_birth(minimum_age=18, maximum_age=25),
                address=fake.address(), email=user.email
            )
            students.append(user)
            # Print credentials for the first 2 students for easy login
            if i < 2:
                self.stdout.write(f"  Created Student -> username: {username} | password: {username}")
        self.stdout.write(self.style.SUCCESS(f'{len(students)} students and profiles created.'))


        self.stdout.write('Creating mess provider users and profiles...')
        for i in range(10):
            # *** MODIFICATION HERE ***
            # Generate username and use it for the password as well
            username = fake.unique.user_name()
            
            user = User.objects.create_user(
                username=username,
                email=fake.email(),
                password=username, # Set password same as username
                role=User.Role.PROVIDER,
                phone=fake.phone_number()[:15]
            )
            MessProviderProfile.objects.create(
                user=user, full_name=fake.name(), phone_no=user.phone, email=user.email,
                mess_name=f"{fake.first_name()}'s Canteen",
                service_type=random.choice([c[0] for c in MessPlan.ServiceType.choices]),
                mess_type=random.choice([c[0] for c in MessPlan.MessType.choices]),
                address=fake.address(), lunch_start=datetime.time(12, 0), lunch_end=datetime.time(14, 30),
                dinner_start=datetime.time(19, 30), dinner_end=datetime.time(22, 0)
            )
            providers.append(user)
            # Print credentials for the first 2 providers for easy login
            if i < 2:
                self.stdout.write(f"  Created Provider -> username: {username} | password: {username}")
        self.stdout.write(self.style.SUCCESS(f'{len(providers)} providers and profiles created.'))
        
        # --- The rest of the script remains the same ---

        # 3. Create Provider-side data
        self.stdout.write('Creating provider-specific data (Menus, Plans, Holidays)...')
        dish_names = [
            "Paneer Butter Masala", "Dal Makhani", "Chole Bhature", "Aloo Gobi", "Malai Kofta", "Rajma Chawal",
            "Veg Biryani", "Shahi Paneer", "Chicken Tikka Masala", "Butter Chicken", "Rogan Josh", "Fish Curry"
        ]
        for provider in providers:
            for dish_name in random.sample(dish_names, random.randint(5, 8)):
                MenuItem.objects.create(provider=provider, dish_name=dish_name, dish_description=fake.paragraph(nb_sentences=2))
            for _ in range(random.randint(2, 4)):
                plan_type, meal_type = random.choice(MessPlan.PlanType.choices)[0], random.choice(MessPlan.MealType.choices)[0]
                coupons = {'MONTHLY': 30, 'YEARLY': 365, 'ONE_TIME': 1}.get(plan_type, 30) * (2 if meal_type == 'BOTH' else 1)
                MessPlan.objects.create(
                    provider=provider, plan_name=f"{plan_type.title()} {meal_type.title()} Plan", plan_type=plan_type,
                    meal_type=meal_type, service_type=random.choice(MessPlan.ServiceType.choices)[0],
                    mess_type=random.choice(MessPlan.MessType.choices)[0], coupons=coupons,
                    price=random.randint(100, 7000), description=fake.paragraph(nb_sentences=3)
                )
            for _ in range(random.randint(0, 3)):
                MessHoliday.objects.create(provider=provider, date=fake.future_date(end_date="+30d"), meal_type=random.choice(MessHoliday.MealType.choices)[0], reason=random.choice(["Weekly Off", "Festival", "Maintenance"]))
            ProviderNotification.objects.create(recipient=provider, message=f"Your weekly report is ready.", is_read=random.choice([True, False]))
        self.stdout.write(self.style.SUCCESS('Provider-specific data created.'))

        # 4. Create Subscription Requests
        self.stdout.write('Creating subscription requests...')
        all_plans = list(MessPlan.objects.all())
        if all_plans:
            for student in students:
                if random.choice([True, False]):
                    plan = random.choice(all_plans)
                    SubscriptionRequest.objects.create(student=student, provider=plan.provider, plan=plan, status=random.choice(["PENDING", "ACCEPTED", "REJECTED"]))
        self.stdout.write(self.style.SUCCESS('Subscription requests created.'))

        # 5. Create Student-side data
        self.stdout.write('Creating student-specific data (Active Subscriptions, Holidays, Notifications)...')
        
        accepted_requests = SubscriptionRequest.objects.filter(status='ACCEPTED')
        active_subscriptions = []
        for request in accepted_requests:
            total_coupons = request.plan.coupons
            sub = ActiveSubscription.objects.create(
                student_profile=request.student.student_profile,
                mess_plan=request.plan,
                total_coupons=total_coupons,
                remaining_coupons=random.randint(1, total_coupons)
            )
            active_subscriptions.append(sub)
        self.stdout.write(self.style.SUCCESS(f'{len(active_subscriptions)} active subscriptions created.'))

        for sub in active_subscriptions:
            for _ in range(random.randint(0, 4)):
                try:
                    StudentHoliday.objects.create(
                        student=sub.student_profile.user,
                        mess_plan=sub.mess_plan,
                        date=fake.future_date(end_date="+30d"),
                        meal_type=random.choice([c[0] for c in StudentHoliday.MEAL_CHOICES]),
                        reason="Personal Leave"
                    )
                except IntegrityError:
                    continue
        self.stdout.write(self.style.SUCCESS('Student holidays created.'))

        for student in students:
            for _ in range(random.randint(1, 3)):
                StudentNotification.objects.create(
                    recipient=student,
                    message=random.choice([
                        "Your request for a monthly plan has been approved.",
                        "Reminder: Mess will be closed this Sunday for maintenance.",
                        "A new 'Special Thali' has been added to our menu. Check it out!",
                        "Your subscription is expiring in 3 days. Please renew to continue service."
                    ]),
                    is_read=random.choice([True, False, False])
                )
        self.stdout.write(self.style.SUCCESS('Student notifications created.'))

        self.stdout.write(self.style.SUCCESS('\n--- All models populated successfully! Your database is ready. ---'))