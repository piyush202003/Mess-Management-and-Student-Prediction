from django.core.management.base import BaseCommand
from django.utils import timezone
from student.models import Attendance, ActiveSubscription, StudentHoliday
from provider.models import MessStatus, MessHoliday
from accounts.models import User

class Command(BaseCommand):
    help = "Automatically mark absent students for a given meal (LUNCH/DINNER)."

    def add_arguments(self, parser):
        parser.add_argument('meal_type', type=str, help='Meal type: LUNCH or DINNER')

    def handle(self, *args, **options):
        meal_type = options['meal_type'].upper()
        today = timezone.localdate()

        mess_statuses = MessStatus.objects.filter(
            date=today,
            meal_type=meal_type,
        )

        total_absents = 0

        for mess_status in mess_statuses:
            provider = mess_status.provider

            # Skip if mess is inactive or on provider holiday
            if not mess_status.is_active:
                continue

            if MessHoliday.objects.filter(provider=provider, date=today, meal_type=meal_type).exists():
                continue

            # Get all students subscribed to this provider
            subs = ActiveSubscription.objects.filter(
                mess_plan__provider=provider,
                is_active=True
            ).select_related('student_profile', 'mess_plan')

            for sub in subs:
                student = sub.student_profile.user

                # Skip if student already marked attendance
                if Attendance.objects.filter(
                    student=student,
                    mess_plan=sub.mess_plan,
                    date=today,
                    meal_type=meal_type
                ).exists():
                    continue

                # Skip if student on holiday
                if StudentHoliday.objects.filter(
                    student=student,
                    mess_plan=sub.mess_plan,
                    date=today,
                    meal_type=meal_type
                ).exists():
                    continue

                # Mark absent and consume coupon
                Attendance.objects.create(
                    student=student,
                    provider=provider,
                    mess_plan=sub.mess_plan,
                    date=today,
                    meal_type=meal_type,
                    status='ABSENT'
                )

                sub.remaining_coupons = max(0, sub.remaining_coupons - 1)
                sub.save()

                total_absents += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Marked {total_absents} students absent for {meal_type} on {today}.")
        )
