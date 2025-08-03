import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_expects_json import expects_json
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_jwt_extended import set_access_cookies, unset_jwt_cookies
from flasgger import swag_from

from app.schemas import schema_register, schema_login
from app.models.user import User, UserDetails
from config import Config

bp = Blueprint('auth', 'auth')
logger = logging.getLogger(__name__)


# refresh the JWT token whenever it gets older than 6 hours
@bp.after_app_request
def refresh_expiring_jwts(response):
    try:
        jwt_token = get_jwt()
        exp_timestamp = jwt_token['exp']
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + Config.JWT_ACCESS_TOKEN_REFRESH)

        # if token is already expired ensure status code is 401 and return the response as is
        if exp_timestamp < datetime.timestamp(now):
            return response

        # if token requires refresh, set new token in cookies
        if target_timestamp > exp_timestamp:
            user_id = get_jwt_identity()
            access_token = create_access_token(user_id)
            set_access_cookies(response, access_token, max_age=Config.JWT_COOKIE_MAX_AGE)

        return response
    except (RuntimeError, KeyError):
        # case where there is not a valid JWT. Just return the original response
        return response


@bp.route('/login', methods=['POST'])
@expects_json(schema_login)
@swag_from('../swagger/login_post.yml')
def login():
    phone = request.json['phone_number']
    password = request.json['password']
    
    found_user = User.objects(phone_number=phone, status='active').first()

    # check if user exists
    if found_user is None:
        return jsonify({'msg': 'user not found'}), 404

    # check password
    if not found_user.check_password(password):
        return jsonify({'msg': 'invalid phone number or password'}), 401

    # form login response
    response = jsonify({
        '_id': found_user._id,
        'username': found_user.details.full_name or found_user.phone_number,
        'role': found_user.role,
    })

    # update last login timestamp
    utc_now = datetime.utcnow()
    found_user.update(last_login=utc_now)

    # create JWT token and set in cookies
    access_token = create_access_token(identity=found_user._id)
    set_access_cookies(response, access_token)

    return response, 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    response = jsonify({'msg': 'logout successful'})
    unset_jwt_cookies(response)
    return response, 200


@bp.route('/register', methods=['POST'])
@expects_json(schema_register)
def register():
    new_user_data = request.json
    phone_number = new_user_data['phone_number']

    # check if user already exists
    found_user = User.objects(phone_number=phone_number).first()
    if found_user:
        if found_user.status == 'active':
            return jsonify({'msg': 'user already exists'}), 409
        elif found_user.status == 'pending_verification':
            return jsonify({'msg': 'user registration pending verification'}), 409

    # create new user
        user = User(
        phone_number=phone_number,
        password=new_user_data["password"],
        details=UserDetails(
            first_name=new_user_data.get("first_name"),
            last_name=new_user_data.get("last_name")
        ),
        status="pending_verification",
            role="user",
        )
        user.save()

    return jsonify({'msg': 'user registered successfully. Please contact admin for verification.'}), 200


@bp.route('/register_confirm', methods=['POST'])
def register_confirm():
    # simple confirmation endpoint for admin use
    phone_number = request.json['phone_number']
    found_user = User.objects(phone_number=phone_number).first()

    if found_user is None:
        return jsonify({'msg': 'user not found'}), 404

    if found_user.status == 'active':
        return jsonify({'msg': 'account already confirmed'}), 422

    # activate user
    found_user.update(status='active')

    return jsonify({'msg': 'account confirmed'}), 200


@bp.route('/change_password', methods=['POST'])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    old_password = request.json['old_password']
    new_password = request.json['new_password']
    
    user = User.objects(_id=user_id).first()
    if not user:
        return jsonify({'msg': 'user not found'}), 404

    # verify old password
    if not user.check_password(old_password):
        return jsonify({'msg': 'old password does not match'}), 409

    # update password
    user.password = new_password
    user.save()
    
    logger.info('user %s successfully changed password', user_id)
    return jsonify({'msg': 'password updated'}), 200
