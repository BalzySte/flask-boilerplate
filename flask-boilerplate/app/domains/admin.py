from typing import List
from functools import wraps
import logging

from flask import Blueprint, jsonify, request, abort, g as g_context
from flask_jwt_extended import jwt_required

from app.models import User
from config import Config

bp = Blueprint('admin', 'admin')
logger = logging.getLogger(__name__)


def admin_required(f):
    """Decorator that requires admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user: User = g_context.current_user
        if user['role'] != 'admin':
            abort(401)
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def admin_users():
    response = {'users': []}
    page = request.args.get('page')
    if page is None:
        page = 0
        response['page_count'], response['total_active_users'] = get_users_page_count()
    else:
        page = int(page)
    users = get_users_page(page)

    # filter out sensitive / unnecessary fields
    for user in users:
        response['users'].append({
            '_id': user.id,
            'full_name': user.details.full_name,
            'phone_number': user.phone_number,
            'balance': user.balance.amount,
            'role': user.role,
            'status': user.status
        })

    return jsonify(response), 200


def get_users_page(page_num, page_size=None) -> List[User]:
    if page_size is None:
        page_size = Config.USERS_PAGE_SIZE
    return User.objects(status='active').skip(page_num * page_size).limit(page_size)


def get_users_page_count(page_size=None):
    if page_size is None:
        page_size = Config.USERS_PAGE_SIZE
    users_count = User.objects(status='active').count()
    return (users_count - 1) // page_size + 1, users_count
