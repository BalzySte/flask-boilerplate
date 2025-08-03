import pytest
import json
import time
import redis
import pika
from unittest.mock import patch
from freezegun import freeze_time

from app.models import Report
from config import Config


@pytest.fixture(scope='module', autouse=True)
def freeze_business_hours():
    """Freeze time to business hours (Tuesday 10:00 AM UTC) for all integration tests"""
    with freeze_time("2025-06-16 10:00:00"):
        yield


@pytest.fixture(scope='module')
def logged_test_client(test_client, init_database):
    """Login as the regular test user and return authenticated test client"""
    # login as the regular user
    login_data = {
        'phone_number': '+19870000002',
        'password': 'qwerty'
    }
    response = test_client.post('/login', json=login_data)
    assert response.status_code == 200
    
    return test_client


def test_report_post_complete_workflow(init_database, logged_test_client, celery_worker):
    """Test complete report generation workflow"""
    test_client = logged_test_client
    
    # mock the build_report function to avoid actual processing delay
    with patch('app.tasks.report.build_report') as mock_build:
        mock_build.return_value = {'test_result': 'integration_test_data'}
        
        # submit report request
        response = test_client.post('/report')
        assert response.status_code == 200
        
        data = response.json
        assert 'report_id' in data
        assert 'task_id' in data
        assert data['msg'] == 'report task submitted successfully'
        
        report_id = data['report_id']
        task_id = data['task_id']
        
        # wait for task to complete (with timeout)
        timeout = 5  # seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # check report status
            report_response = test_client.get(f'/report/{report_id}')
            assert report_response.status_code == 200
            
            report_data = report_response.json
            if report_data['status'] == 'completed':
                # verify the report was completed successfully
                assert report_data['task_id'] == task_id
                assert report_data['result_data'] == {'test_result': 'integration_test_data'}
                assert report_data['completed_at'] is not None
                assert report_data['error_message'] is None
                
                # verify database state
                report = Report.objects(_id=report_id).first()
                assert report.status == 'completed'
                assert report.result_data == {'test_result': 'integration_test_data'}
                
                return  # test passed
            
            time.sleep(0.5)  # wait before checking again
        
        # if we get here, the task didn't complete in time
        pytest.fail(f"Report task did not complete within {timeout} seconds")


def test_redis_event_complete_workflow(init_database, logged_test_client):
    """Test Redis pub/sub event publishing and receiving"""
    test_client = logged_test_client
    
    # set up Redis subscriber to capture published messages
    redis_client = redis.from_url(Config.REDIS_EVENTS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    pubsub.subscribe('events:event')
    
    try:
        # submit Redis event request
        response = test_client.post('/redis-pubsub-event')
        print(response.json)
        assert response.status_code == 200
        assert response.json['message'] == 'Redis event published'
        
        # wait for and verify the published message
        timeout = 5  # seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            message = pubsub.get_message(timeout=1)
            if message and message['type'] == 'message':
                # parse the event data
                event_data = json.loads(message['data'])
                
                # verify message structure
                assert event_data['type'] == 'a-simple-event'
                assert 'timestamp' in event_data
                assert 'data' in event_data
                
                # verify event data contains expected fields
                data = event_data['data']
                assert 'user_id' in data
                assert data['a_field'] == 'a_value'
                assert data['another_field'] == 'another_value'
                
                return  # test passed
        
        pytest.fail(f"No Redis message received within {timeout} seconds")
        
    finally:
        pubsub.unsubscribe('events:event')
        pubsub.close()
        redis_client.close()


def test_rabbitmq_event_complete_workflow(init_database, logged_test_client):
    """Test RabbitMQ event publishing and receiving"""
    test_client = logged_test_client
    
    # set up RabbitMQ consumer to capture published messages
    connection = pika.BlockingConnection(Config.FLASK_PIKA_PARAMS)
    channel = connection.channel()
    
    # ensure queue exists
    queue_name = 'events.a-complex-event'
    channel.queue_declare(queue=queue_name, durable=True)
    
    # clear any existing messages
    channel.queue_purge(queue_name)
    
    try:
        # submit RabbitMQ event request
        response = test_client.post('/rabbitmq-event')
        print(response.json)
        assert response.status_code == 200
        assert response.json['message'] == 'RabbitMQ event published'
        
        # wait for and verify the published message
        timeout = 5  # seconds
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            method_frame, header_frame, body = channel.basic_get(queue=queue_name)
            
            if method_frame:
                # parse the event data
                event_data = json.loads(body)
                
                # verify message structure
                assert event_data['type'] == 'a-complex-event'
                assert 'timestamp' in event_data
                assert 'data' in event_data
                
                # verify event data contains expected fields
                data = event_data['data']
                assert 'user_id' in data
                assert data['a_field'] == 'a_value'
                assert data['another_field'] == 'another_value'
                
                # verify message properties
                assert header_frame.content_type == 'application/json'
                
                # acknowledge the message
                channel.basic_ack(method_frame.delivery_tag)
                
                return  # test passed
            
            time.sleep(0.5)  # wait before checking again
        
        pytest.fail(f"No RabbitMQ message received within {timeout} seconds")
        
    finally:
        connection.close()
