from app.websocket.events import events_websocket_endpoint

from starlette.applications import Starlette
from starlette.routing import WebSocketRoute


def create_app():
    return Starlette(
        routes=[WebSocketRoute('/ws', events_websocket_endpoint)]
    )
