import logging.config
from celery.schedules import crontab
from celery.signals import after_setup_task_logger

from app import create_app
from app import celery
from app.tasks import disable_inactive_users
from app.logs import logging_config_celery

app = create_app()
app.app_context().push()


# configure application logging
def initialize_logging(logger=None, loglevel=logging.INFO, **kwargs):
    logging.config.dictConfig(logging_config_celery)


after_setup_task_logger.connect(initialize_logging)


@celery.on_after_configure.connect
def setup_scheduled_tasks(sender, **kwargs):
    # run disable_inactive_users every day at 12AM
    sender.add_periodic_task(
        crontab(hour='0', minute='0'),
        disable_inactive_users.s(),
        name='disable_inactive_users'
    )


if __name__ == '__main__':
    argv = [
        'worker',
        '--loglevel=DEBUG',
    ]
    celery.worker_main(argv)
