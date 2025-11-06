from celery import shared_task
from django.utils import timezone
from accounts.models import User
from .ml.provider_model import retrain_provider_model, check_retraining_needed
import logging

logger = logging.getLogger(__name__)


@shared_task
def auto_retrain_provider_models():
    """
    Automated task to retrain provider models that need updating.
    Run this daily via Celery Beat.
    """
    logger.info("Starting automated model retraining check")
    
    providers = User.objects.filter(role='PROVIDER')
    
    retrained_count = 0
    skipped_count = 0
    failed_count = 0
    
    for provider in providers:
        try:
            needs_retrain, reason = check_retraining_needed(provider.id)
            
            if needs_retrain:
                logger.info(f"Retraining model for provider {provider.username}: {reason}")
                metadata = retrain_provider_model(provider.id, auto_retrain=True)
                logger.info(f"Successfully retrained model for {provider.username}")
                retrained_count += 1
            else:
                logger.info(f"Skipping {provider.username}: {reason}")
                skipped_count += 1
        
        except ValueError as e:
            logger.warning(f"Cannot retrain {provider.username}: {e}")
            skipped_count += 1
        except Exception as e:
            logger.error(f"Error retraining {provider.username}: {e}")
            failed_count += 1
    
    summary = {
        'timestamp': timezone.now().isoformat(),
        'total_providers': providers.count(),
        'retrained': retrained_count,
        'skipped': skipped_count,
        'failed': failed_count
    }
    
    logger.info(f"Automated retraining completed: {summary}")
    return summary


@shared_task
def retrain_single_provider(provider_id):
    """
    Task to retrain a single provider's model.
    Can be triggered manually or scheduled.
    """
    try:
        logger.info(f"Retraining model for provider {provider_id}")
        metadata = retrain_provider_model(provider_id, auto_retrain=False)
        return {'success': True, 'metadata': metadata}
    except Exception as e:
        logger.error(f"Error retraining provider {provider_id}: {e}")
        return {'success': False, 'error': str(e)}
