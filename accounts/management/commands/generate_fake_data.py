from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import random
from accounts.models import *
from provider.models import *
from student.models import *

fake = Faker()

class Command(BaseCommand):
    help = "Generate fake data for mess management system"

    def handle(self, *args, **kwargs):
        Faker.seed(42)
        random.seed(42)
        self.stdout.write('Clearing old data...')
        StudentHoliday.objects.all().delete()
        ActiveSubscription.objects.all().delete()
        Notification.objects.all().delete()
        SubscriptionRequest.objects.all().delete()
        MessHoliday.objects.all().delete()
        MenuItem.objects.all().delete()
        ProviderNotification.objects.all().delete()
        MessPlan.objects.all().delete()
        StudentProfile.objects.all().delete()
        MessProviderProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.SUCCESS('Old data cleared successfully.'))
        # === 1️⃣ Create Providers ===
        # providers = []
        # for _ in range(5):
        #     username = fake.unique.user_name()
        #     user = User.objects.create_user(
        #         username=username,
        #         email=fake.email(),
        #         role="PROVIDER",
        #         phone=fake.phone_number(),
        #         password=username,  # username = password
        #     )
        #     MessProviderProfile.objects.create(
        #         user=user,
        #         full_name=fake.name(),
        #         phone_no=user.phone,
        #         email=user.email,
        #         mess_name=fake.company(),
        #         address=fake.address(),
        #         service_type=random.choice(["DINING", "TIFFIN", "BOTH"]),
        #         mess_type=random.choice(["VEG", "NON-VEG", "BOTH"]),
        #         lunch_start=fake.time_object(),
        #         lunch_end=fake.time_object(),
        #         dinner_start=fake.time_object(),
        #         dinner_end=fake.time_object(),
        #     )
        #     providers.append(user)

        # self.stdout.write(self.style.SUCCESS(f"✅ Created {len(providers)} Mess Providers"))

        # # === 2️⃣ Create Students ===
        # students = []
        # for _ in range(50):
        #     username = fake.unique.user_name()
        #     user = User.objects.create_user(
        #         username=username,
        #         email=fake.email(),
        #         role="STUDENT",
        #         phone=fake.phone_number(),
        #         password=username,  # username = password
        #     )
        #     StudentProfile.objects.create(
        #         user=user,
        #         full_name=fake.name(),
        #         phone_no=user.phone,
        #         gender=random.choice(["Male", "Female"]),
        #         dob=fake.date_of_birth(minimum_age=18, maximum_age=25),
        #         address=fake.address(),
        #         email=user.email,
        #     )
        #     students.append(user)

        # self.stdout.write(self.style.SUCCESS(f"✅ Created {len(students)} Students"))

        # # === 3️⃣ Create Mess Plans per Provider ===
        # plans = []
        # for provider in providers:
        #     for _ in range(random.randint(2, 4)):
        #         plan = MessPlan.objects.create(
        #             provider=provider,
        #             plan_name=fake.word().capitalize() + " Plan",
        #             plan_type=random.choice(["MONTHLY", "YEARLY", "ONE_TIME"]),
        #             meal_type=random.choice(["LUNCH", "DINNER", "BOTH"]),
        #             service_type=random.choice(["DINING", "TIFFIN", "BOTH"]),
        #             mess_type=random.choice(["VEG", "NON-VEG", "BOTH"]),
        #             coupons=random.randint(20, 60),
        #             price=round(random.uniform(1000, 4000), 2),
        #             description=fake.sentence(),
        #         )
        #         plans.append(plan)

        # self.stdout.write(self.style.SUCCESS(f"✅ Created {len(plans)} Mess Plans"))

        # # === 4️⃣ Create Menu Items (15–20 per Provider) ===
        # # === 4️⃣ Create Menu Items (15–20 per Provider) ===
        # menu_count = 0
        # for provider in providers:
        #     dish_names = set()
        #     for i in range(random.randint(15, 20)):
        #         # Ensure unique dish name per provider
        #         base_name = fake.word().capitalize()
        #         while base_name in dish_names:
        #             base_name = fake.word().capitalize()
        #         dish_names.add(base_name)

        #         MenuItem.objects.create(
        #             provider=provider,
        #             dish_name=base_name,
        #             dish_description=fake.sentence(),
        #         )
        #         menu_count += 1

        # self.stdout.write(self.style.SUCCESS(f"✅ Created {menu_count} Menu Items"))


        # # === 5️⃣ Create One Active Subscription per Student ===
        # for student in students:
        #     plan = random.choice(plans)
        #     ActiveSubscription.objects.create(
        #         student_profile=student.student_profile,
        #         mess_plan=plan,
        #         total_coupons=plan.coupons,
        #         remaining_coupons=random.randint(0, plan.coupons),
        #         is_active=True,
        #     )

        # self.stdout.write(self.style.SUCCESS(f"✅ Each of {len(students)} Students subscribed to a Mess Plan"))

        # # === 6️⃣ Create Random Attendance Records for Past 7 Days ===
        # today = timezone.now().date()
        # for sub in ActiveSubscription.objects.all():
        #     for i in range(7):  # last 7 days
        #         Attendance.objects.create(
        #             student=sub.student_profile.user,
        #             mess_plan=sub.mess_plan,
        #             provider=sub.mess_plan.provider,
        #             date=today - timezone.timedelta(days=i),
        #             meal_type=random.choice(["lunch", "dinner"]),
        #             status=random.choice(["PRESENT", "ABSENT", "PERSONAL_HOLIDAY", "MESS_HOLIDAY"]),
        #         )

        # self.stdout.write(self.style.SUCCESS("✅ Attendance Records Created (7 days per student)"))

        # # === 7️⃣ Optional: Add a Few Mess Holidays ===
        # for provider in providers:
        #     for _ in range(random.randint(1, 2)):
        #         MessHoliday.objects.create(
        #             provider=provider,
        #             date=today - timezone.timedelta(days=random.randint(1, 10)),
        #             meal_type=random.choice(["LUNCH", "DINNER"]),
        #             reason=random.choice(["Maintenance", "Festival", "Staff Shortage"]),
        #         )

        # self.stdout.write(self.style.SUCCESS("✅ Mess Holidays Added"))

        # self.stdout.write(self.style.SUCCESS("🎉 Fake data generation complete!"))
