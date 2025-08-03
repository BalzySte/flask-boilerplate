from functools import wraps
from typing import Callable
from datetime import datetime

from flask import jsonify


def time_restricted(time_restriction: Callable[[datetime], bool], msg: str = None):
    # allow the decorated method only if current timestamp is evaluated positively by
    # the provided time_restriction function
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            now = datetime.utcnow()
            allowed = time_restriction(now)
            if not allowed:
                not_allowed_msg = msg or 'Service Unavailable. This endpoint is time-constrained'
                return jsonify({'msg': not_allowed_msg}), 503
            return f(*args, **kwargs)
        return decorated_function
    return decorator
