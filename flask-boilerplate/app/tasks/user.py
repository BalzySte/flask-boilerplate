from datetime import datetime, timedelta
from celery.utils.log import get_task_logger

from app import celery
from app.models import User


logger = get_task_logger(__name__)


@celery.task
def disable_inactive_users():
    """ Disable users who have not logged in for a long time """
    utc_now = datetime.utcnow()
    inactivity_threshold = utc_now - timedelta(days=365)

    # Use efficient bulk update to disable inactive users
    # Only update users who are currently active and haven't logged in for 1+ year
    disabled_count = User.objects(
        last_login__lte=inactivity_threshold,
        status='active'
    ).update(
        set__status='inactive',
    )

    logger.info(f'disabled {disabled_count} inactive users')
    return {
        'disabled_users': disabled_count,
        'inactive_since': inactivity_threshold.strftime('%Y-%m-%d')
    }
