import os
import hashlib
import logging
from datetime import datetime

from flask import request, jsonify, g as g_context
from flask import Blueprint
from flask_expects_json import expects_json
from flask_jwt_extended import jwt_required
from flask_marshmallow.fields import fields as ma_fields
from werkzeug.utils import secure_filename

from app import ma, api_spec, MEDIA_BUCKET
from app.models import User
from app.models.user import Contacts
from app.schemas import schema_user_put, schema_user_contacts_post

from config import Config


bp = Blueprint('user', 'user')
logger = logging.getLogger(__name__)


class UserDetailsSchema(ma.Schema):
    first_name = ma_fields.String(required=True)
    last_name = ma_fields.String(required=True)
    date_of_birth = ma_fields.DateTime(required=True)


class ContactSchema(ma.Schema):
    contact = ma_fields.String(required=True)


class UserContactsSchema(ma.Schema):
    email = ma_fields.Nested(ContactSchema())
    telegram = ma_fields.Nested(ContactSchema())


user_details_schema = UserDetailsSchema()
user_contacts_schema = UserContactsSchema()

# add Marshmallow schemas to APISpec
api_spec.components.schema('UserDetails', schema=UserDetailsSchema)
api_spec.components.schema('UserContacts', schema=UserContactsSchema)


@bp.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    user: User = g_context.current_user

    return jsonify({
        '_id': user._id,
        'details': user_details_schema.dump(user.details),
        'profile_picture': user.profile_picture,
        'phone_number': user.phone_number,
        'signup_date': user.signup_date,
        'role': user.role,
        'status': user.status,
        'balance': {
            'amount': user.balance.amount,
            'last_topup': user.balance.last_topup
        },
        'contacts': user_contacts_schema.dump(user.contacts),
    }), 200


@bp.route('/user', methods=['PUT'])
@jwt_required()
@expects_json(schema_user_put)
def put_user():
    """ Updates user details (all fields: first_name, last_name, date_of_birth) """
    user: User = g_context.current_user
    update_data = request.json

    # Parse date_of_birth from string to datetime object
    try:
        date_of_birth = datetime.strptime(update_data['date_of_birth'], '%Y-%m-%d')
    except ValueError:
        return jsonify({'msg': 'invalid date format, use YYYY-MM-DD'}), 400

    # Update all user details fields together
    modified = user.modify(
        details__first_name=update_data['first_name'],
        details__last_name=update_data['last_name'],
        details__date_of_birth=date_of_birth
    )

    if not modified:
        return jsonify({'msg': 'user update failed'}), 500

    return jsonify({'_id': user.id}), 200


@bp.route('/user/contacts', methods=['POST'])
@jwt_required()
@expects_json(schema_user_contacts_post)
def user_contacts_post():
    """ Set user contacts (email and Telegram ID) """
    user: User = g_context.current_user
    
    # contact fields shall either hold a valid contact for the specified channel or None
    for contact_type in request.json:
        contact = request.json[contact_type]
        # if provided contact is None delete it from the database
        if contact is None:
            user.contacts[contact_type] = None
            continue
        # else set the new value
        me_contact_class = user.contacts._fields[contact_type].document_type
        user.contacts[contact_type] = me_contact_class(contact=contact)
    user.save()
    
    return jsonify({'contacts': user_contacts_schema.dump(user.contacts)}), 200


@bp.route('/user/profile-picture', methods=['POST'])
@jwt_required()
def user_profile_picture_post():
    user = g_context.current_user

    file = request.files.get('file')
    if not file:
        return jsonify({'msg': 'no file provided'}), 400

    filename = secure_filename(file.filename)
    file_extension = os.path.splitext(filename)[1]

    if file_extension not in Config.PROFILE_PIC_ALLOWED_EXTENSIONS:
        return jsonify({'msg': 'invalid file type'}), 400

    # get the length of the stream to check if it exceeds the limit
    file_length = file.stream.seek(0, os.SEEK_END)
    file.stream.seek(0)

    if file_length > Config.PROFILE_PIC_MAX_SIZE:
        logger.info(f'media file too large - size {file_length} bytes')
        return jsonify({'msg': 'file too large'}), 400

    # compute the md5sum of the user_id + file content for the resource name
    # this avoids duplication of files on a per-user basis
    resource_hash = hashlib.md5()
    resource_hash.update(bytes.fromhex(user.id or ''))
    resource_hash.update(file.stream.read())
    resource_hash = resource_hash.digest()
    file.stream.seek(0)

    # inferring the mime type from the file extension
    # should verify the file contents with magic library in production
    mime_type = f'image/{file_extension[1:]}'

    resource_path = f'profile-pic/{user.id}{file_extension}'

    MEDIA_BUCKET.upload_fileobj(
        file.stream,
        resource_path,
        ExtraArgs={
            'ACL': 'public-read',
            'ContentType': mime_type,
            'Metadata': {'user': user.id or 'unauthenticated'}
        }
    )

    user.profile_picture = f'{Config.MEDIA_BASE_URL}/{resource_path}'
    user.save()

    return jsonify({'msg': 'success'}), 200 
