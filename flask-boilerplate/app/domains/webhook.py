from functools import wraps
from flask import Blueprint
from flask_expects_json import expects_json
from flask import request, jsonify, g as g_context

import logging

from app.models import User
from app.schemas import schema_webhook_alert_post


bp = Blueprint('webhook', 'webhook')
logger = logging.getLogger(__name__)


def webhook_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.json.get('access_token') or request.args.get('access_token')

        try:
            user: User = User.objects(access_token=access_token).get()
            user_id = user._id
        
        except User.DoesNotExist:
            # if token not found, return 401 error
            return jsonify({'msg': 'Invalid access token'}), 401
        
        g_context.user_id = user_id
        
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/webhook/<event>', methods=['POST'])
@expects_json(schema_webhook_alert_post)
@webhook_token_required
def webhook_post(event):
    user_id = g_context.user_id
    logger.info(f'received {event} webhook for user {user_id}')

    # store / process the received webhook event
    # ...

    return 'Accepted', 200
