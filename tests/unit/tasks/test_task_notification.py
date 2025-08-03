from unittest.mock import patch, MagicMock

from app.domains.event import publish_redis_event, publish_rabbitmq_event


def test_redis_event_publishing():
    """Test Redis pub/sub event publishing"""
    event_type = 'a-simple-event'
    test_data = {
        'user_id': '61d2fb409606db54d47d15c3',
        'message': 'test redis event',
        'data': {'key': 'value'}
    }
    
    # Mock the Redis client
    with patch('app.domains.event.redis_client') as mock_redis:
        mock_redis.publish = MagicMock()
        
        # Call the function
        publish_redis_event(event_type, test_data)
        
        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()
        
        # Get the call arguments
        call_args = mock_redis.publish.call_args
        channel, message = call_args[0]
        
        assert channel == 'events:event'
        # Verify the message contains our data (it's JSON encoded)
        assert b'test redis event' in message
        assert b'61d2fb409606db54d47d15c3' in message
        assert b'a-simple-event' in message


def test_rabbitmq_event_publishing():
    """Test RabbitMQ event publishing"""
    event_type = 'a-complex-event'
    test_data = {
        'user_id': '61d2fb409606db54d47d15c3',
        'message': 'test rabbitmq event',
        'data': {'complex': 'structure'}
    }
    
    # Mock the pika channel
    mock_channel = MagicMock()
    
    with patch('app.domains.event.pika_client') as mock_pika:
        mock_pika.channel.return_value = mock_channel
        
        # Call the function
        publish_rabbitmq_event(event_type, test_data)
        
        # Verify channel methods were called
        mock_pika.channel.assert_called_once()
        mock_channel.basic_publish.assert_called_once()
        mock_pika.return_channel.assert_called_once_with(mock_channel)
        
        # Get the publish call arguments
        publish_call = mock_channel.basic_publish.call_args
        kwargs = publish_call[1]
        
        assert kwargs['exchange'] == 'events'
        assert kwargs['routing_key'] == 'a-complex-event'
        
        # Verify the message body contains our data
        body = kwargs['body']
        assert b'test rabbitmq event' in body
        assert b'61d2fb409606db54d47d15c3' in body
        assert b'a-complex-event' in body
