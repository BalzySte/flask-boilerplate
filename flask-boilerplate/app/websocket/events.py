import logging
import redis
import asyncio
import orjson

from starlette.websockets import WebSocket, WebSocketState

from app.websocket.jwt import websocket_auth
from app.websocket.utils import pubsub_listener, websocket_listener
from config import Config

logger = logging.getLogger(__name__)


# redis connection for pub/sub
redis_client: redis.asyncio.Redis = redis.asyncio.from_url(Config.REDIS_EVENTS_URL, decode_responses=True)


async def process_event_message(message: bytes):
    """Process incoming Redis pub/sub message and forward to websocket client"""
    try:
        # parse the JSON message from Redis
        event_data = orjson.loads(message)
        logger.debug(f'Received event: {event_data}')
        return event_data
    
    except Exception as e:
        logger.error(f'Failed to process event message: {str(e)}')
        return None


@websocket_auth
async def events_websocket_endpoint(websocket: WebSocket, user_id: str):
    """Generic websocket endpoint that listens to Redis pub/sub events and forwards them to clients"""
    redis_pubsub = redis_client.pubsub()
    
    # subscribe to general events channel
    # clients can subscribe to specific channels based on their needs
    events_channel = 'events:event'
    
    await redis_pubsub.subscribe(events_channel)
    await websocket.accept()
    
    logger.info(f'User {user_id} connected to events websocket')

    # sender task relays events from redis pub/sub to websocket client
    # listener task waits for client disconnection
    sender = asyncio.create_task(
        pubsub_listener(redis_pubsub, process_event_message, events_channel, websocket)
    )
    listener = asyncio.create_task(websocket_listener(websocket))

    # wait for client disconnection
    await listener

    # cleanup: cancel sender task if still running
    sender.cancel()

    # close websocket if still open
    if websocket.client_state == WebSocketState.CONNECTED:
        await websocket.close()

    # cleanup: unsubscribe and close Redis connection
    await redis_pubsub.unsubscribe(events_channel)
    await redis_pubsub.close()

    logger.info(f'Closed events websocket for user {user_id}')
