from django.core.management.base import BaseCommand
from mess_app.ml.provider_model import update_prediction_actuals


class Command(BaseCommand):
    help = 'Update prediction logs with actual attendance data'

    def handle(self, *args, **options):
        self.stdout.write('Updating prediction logs...')
        
        try:
            count = update_prediction_actuals()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Successfully updated {count} prediction logs'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error updating predictions: {str(e)}')
            )
