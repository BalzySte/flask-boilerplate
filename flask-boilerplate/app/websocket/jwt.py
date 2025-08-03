from typing import Callable
from functools import wraps

import jwt
from starlette.websockets import WebSocket

from config import Config
import logging


logger = logging.getLogger(__name__)


# JWT Decoder
def decode_jwt_token(token):
    try:
        # Decode the token header first to determine the algorithm
        unverified_header = jwt.get_unverified_header(token)
        alg = str(unverified_header['alg']).upper()

        # We only support HS256 symmetric encryption
        if alg != 'HS256':
            raise Exception(f'Unsupported algorithm: {alg}. Only HS256 is supported.')

        # Decode the token using the secret key
        payload: dict = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    
    except jwt.ExpiredSignatureError:
        raise Exception('Token has expired')
    
    except jwt.InvalidTokenError:
        raise Exception(f'Invalid access token')


# Decorator to check authentication from websocket cookies (JWT)
def websocket_auth(func: Callable):

    @wraps(func)
    async def wrapper(websocket: WebSocket, *args, **kwargs):
        # Fetch token from cookies (based on your Flask config)
        token = websocket.cookies.get('access_token_cookie')
        
        try:
            if token is None:
                raise Exception('No access token provided')
            
            decoded_token = decode_jwt_token(token)
            user_id = decoded_token.get('sub')

            if not user_id:
                raise Exception('Invalid token: no user ID found')
            
        except Exception as e:
            logger.exception(f'Error authenticating WebSocket connection: {token}')

            await websocket.accept()
            await websocket.send_json({'auth_error': str(e)})
            await websocket.close(code=1008)  # Close connection for invalid token

            return
            
        # Continue with WebSocket handling
        return await func(websocket, user_id, *args, **kwargs)
    
    return wrapper
