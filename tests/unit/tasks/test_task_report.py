from unittest.mock import patch

from app.models import Report
from app.tasks.report import process_report


def test_process_report_task(init_database):
    """Test the process_report celery task with existing user data"""
    # use existing regular user from test data
    user_id = '61d2fb409606db54d47d15c3'  # Regular user from users.json
    
    # create a test report
    report = Report(
        user=user_id,
        task_id='test-task-123',
        status='pending'
    )
    report.save()
    
    task_data = {
        'user_id': user_id,
        'report_id': str(report._id)
    }
    
    # mock the build_report function to skip the computation (long sleep in this example)
    with patch('app.tasks.report.build_report') as mock_build:
        mock_build.return_value = {'result': 'success', 'data': 'processed'}
        
        result = process_report(task_data)
        
        # verify task result
        assert result['status'] == 'completed'
        assert result['report_id'] == str(report._id)
        
        # verify report was updated in database
        updated_report = Report.objects(_id=report._id).get()
        assert updated_report.status == 'completed'
        assert updated_report.completed_at is not None
        assert updated_report.result_data == {'result': 'success', 'data': 'processed'}
        assert updated_report.error_message is None
