from django.core.management.base import BaseCommand
from accounts.models import User
from mess_app.ml.provider_model import retrain_provider_model
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Retrain models for all providers with sufficient data'

    def handle(self, *args, **options):
        providers = User.objects.filter(role='PROVIDER')
        
        self.stdout.write(f'Found {providers.count()} providers')
        
        success_count = 0
        failed_count = 0
        
        for provider in providers:
            try:
                self.stdout.write(f'Training model for {provider.username}...')
                metadata = retrain_provider_model(provider.id)
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ Success: {metadata["n_samples"]} samples, '
                    f'Avg: {metadata["avg_attendance"]:.1f}'
                ))
                success_count += 1
            except ValueError as e:
                self.stdout.write(self.style.WARNING(f'  ⊘ Skipped: {str(e)}'))
                failed_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                failed_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\nCompleted: {success_count} successful, {failed_count} failed/skipped'
        ))
