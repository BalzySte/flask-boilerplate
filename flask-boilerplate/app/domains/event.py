import logging
from datetime import datetime, time
import orjson
from typing import Dict
import pika

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import redis_client, pika_client
from app.utils.time_restrictions import time_restricted
from config import EVENT_TYPES

bp = Blueprint('event', 'event')
logger = logging.getLogger(__name__)


def business_hours(timestamp: datetime = None) -> bool:
    """Check if current time is within business hours (9 AM to 5 PM)"""
    
    # business hours: 9 AM to 5 PM, Monday to Friday
    weekday = timestamp.weekday()
    if weekday > 4:
        return False
    
    if timestamp.time() < time(9, 0) or timestamp.time() > time(17, 0):
        return False
    
    return True
    


def publish_redis_event(event_type: str, data: Dict):
    """Publish event to Redis pub/sub"""
    
    if event_type not in EVENT_TYPES:
        raise ValueError(f'Invalid event type: {event_type}')
    
    event_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': event_type,
        'data': data
    }
    
    redis_client.publish('events:event', orjson.dumps(event_data))


def publish_rabbitmq_event(event_type: str, data: Dict):
    """Publish event to RabbitMQ"""
    
    if event_type not in EVENT_TYPES:
        raise ValueError(f'Invalid event type: {event_type}')
    
    event_data = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': event_type,
        'data': data
    }
    
    # get a channel from flask-pika
    channel = pika_client.channel()
    
    try:
        # publish message
        channel.basic_publish(
            exchange='events',
            routing_key=event_type,
            body=orjson.dumps(event_data),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
        
        logger.info(f"Published RabbitMQ event: {event_type}")
        
    except Exception as e:
        logger.error(f"Failed to publish RabbitMQ event: {str(e)}")
        raise

    finally:
        # return the channel to the pool
        pika_client.return_channel(channel)


@bp.route('/redis-pubsub-event', methods=['POST'])
@jwt_required()
@time_restricted(business_hours, msg="Only available during business hours")
def redis_event_post():
    """Demonstrates Redis pub/sub messaging"""
    event_type = 'a-simple-event'
    user_id = get_jwt_identity()

    # publish event
    event_data = {
        'user_id': user_id,
        'a_field': 'a_value',
        'another_field': 'another_value'
    }
    
    publish_redis_event(event_type, event_data)
        
    return jsonify({'message': 'Redis event published'}), 200


@bp.route('/rabbitmq-event', methods=['POST'])
@jwt_required()
@time_restricted(business_hours, msg="Only available during business hours")
def rabbitmq_event_post():
    """Demonstrates RabbitMQ messaging"""
    event_type = 'a-complex-event'
    user_id = get_jwt_identity()

    # publish event
    event_data = {
        'user_id': user_id,
        'a_field': 'a_value',
        'another_field': 'another_value'
    }
    
    try:
        publish_rabbitmq_event(event_type, event_data)
        return jsonify({'message': 'RabbitMQ event published'}), 200
    except Exception as e:
        logger.error(f"Failed to publish RabbitMQ event: {str(e)}")
        return jsonify({'error': 'Failed to publish event'}), 500
