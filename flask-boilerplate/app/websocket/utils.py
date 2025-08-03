from typing import Callable
from redis.client import PubSub
from starlette.websockets import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

import logging

logger = logging.getLogger(__name__)


async def websocket_listener(websocket: WebSocket):
    # keep listening for a client disconnect
    while True:
        try:
            await websocket.receive_bytes()
        except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError):
            break


async def pubsub_listener(
    channel: PubSub, callback: Callable, 
    channel_id: str, websocket: WebSocket,
    timeout: int = 60
):
    while True:
        # noinspection PyBroadException
        message = None
        try:
            message = await channel.get_message(ignore_subscribe_messages=True, timeout=timeout)
            if message is None or message['type'] != 'message':
                continue

            # process the message payload
            payload = message['data']

            # send message
            response = await callback(payload)
            
            if response:
                await websocket.send_json(response)

        except (WebSocketDisconnect, ConnectionClosedOK, ConnectionClosedError) as exc:
            logger.info(f'websocket disconnected for channel {channel_id} - {exc}: {message}')
            break

        except Exception:
            logger.exception(f'error in websocket for channel {channel_id}: {message}')
            continue
