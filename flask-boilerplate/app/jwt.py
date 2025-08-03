from flask import g as g_context
from flask_jwt_extended import JWTManager

from app.models.user import User


jwt = JWTManager()


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_headers, jwt_payload):
    user_id = jwt_payload['sub']

    try:
        user = User.objects(_id=user_id).get()
    except User.DoesNotExist:
        return None

    # flask_jwt_extended sets the user object in the request context (g_context) in a "_jwt_extended_jwt_user"
    # attribute and exposes it through the "current_user" object or get_current_user() function
    # however the same User object is also referenced in "g_context.current_user" to provide an interface
    # that is independent of the JWT extension (for example: should the authentication method change in the future)
    g_context.current_user = user
    return user
