import time
from datetime import datetime
from celery.utils.log import get_task_logger

from app import celery
from app.models import Report

logger = get_task_logger(__name__)


def build_report(data):
    # simulate processing work
    time.sleep(10)
    return data


@celery.task
def process_report(task_data):
    """
    Simple report processing task that saves results to database.
    """
    user_id = task_data['user_id']
    report_id = task_data['report_id']
    data = {'foo': 'bar'}  # mock data

    # get the report record
    try:
        report: Report = Report.objects(_id=report_id).get()
        report.status = 'running'
        report.save()
    except Report.DoesNotExist:
        logger.error(f'Report {report_id} not found')
        return {'status': 'failed', 'error': 'Report not found'}

    logger.info(f'Processing report {report_id} for user {user_id}')
        
    try:
        result_data = build_report(data)
    except Exception as exc:
        logger.error(f'Error building report: {str(exc)}')
        report.status = 'failed'
        report.error_message = str(exc)
        report.save()
        return {'status': 'failed', 'error': str(exc)}
        
    # mark report as completed
    report.status = 'completed'
    report.completed_at = datetime.utcnow()
    report.result_data = result_data
    report.save()

    logger.info(f'Completed report processing for user {user_id}')
    return {'status': 'completed', 'report_id': report_id}
