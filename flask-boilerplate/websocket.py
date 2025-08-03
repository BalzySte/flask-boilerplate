import logging.config

from app.logs import websocket_logging_config
from app.websocket import create_app

# configure application logging
logging.config.dictConfig(websocket_logging_config)

app = create_app()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("websocket:app", host='0.0.0.0', port=5000, reload=True)
