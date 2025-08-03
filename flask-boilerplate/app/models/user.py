import re
import random
import string
from datetime import datetime
from typing import Union

import bcrypt
import mongoengine as db
from mongoengine import EmbeddedDocument

from app.models.base_document import BaseDocument


def generate_random_token():
    # NOTE: there's a rare chance of collision with existing tokens here
    #       there should be a retry strategy in production
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


class UserDetails(EmbeddedDocument):
    first_name = db.StringField(required=True, max_length=100)
    last_name = db.StringField(required=True, max_length=100)
    date_of_birth = db.DateTimeField(null=True)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Balance(EmbeddedDocument):
    amount = db.IntField(required=True, default=0)
    last_topup = db.DateTimeField(null=True)


def validate_email(email: str):
    if not re.fullmatch(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+', email):
        raise db.errors.ValidationError(f'Invalid email address: {email}')


def validate_telegram_username(username: str):
    # A-z, a-z, 0-9 and underscores of length 5 to 32, starts with alphabet
    if not re.fullmatch(r'[A-Za-z]{1}[a-zA-Z0-9_]{4,31}', username):
        raise db.errors.ValidationError(f'Invalid Telegram username: {username}')


def validate_telegram_chat_id(user_id: str):
    # Telegram IDs are max 52 bits long and can fit in a 64-bit integer according to documentation
    # 64 bit ints can be as big as 20-digit numbers
    if not re.fullmatch(r'[0-9]{1,20}', user_id):
        raise db.errors.ValidationError(f'Invalid Telegram chat ID: {user_id}')


class EmailContact(EmbeddedDocument):
    contact = db.StringField(required=True, validation=validate_email, max_length=254)


class TelegramContact(EmbeddedDocument):
    contact = db.StringField(required=True, validation=validate_telegram_username, max_length=32)
    chat_id = db.StringField(default=True, null=True, validation=validate_telegram_chat_id, max_length=20)


class Contacts(EmbeddedDocument):
    email: Union[EmailContact, None] = db.EmbeddedDocumentField(EmailContact, default=EmailContact, null=True)
    telegram: Union[TelegramContact, None] = db.EmbeddedDocumentField(TelegramContact, default=TelegramContact, null=True)


class User(BaseDocument):
    meta = {'collection': 'users'}

    # authentication
    phone_number = db.StringField(required=True)
    password = db.BinaryField(required=True)
    access_token = db.StringField(required=True, default=generate_random_token)

    # role and status
    role = db.StringField(required=True, choices=['user', 'admin'])
    status = db.StringField(required=True, choices=['active', 'deactivated', 'pending_verification'])

    # profile and contacts
    details: UserDetails = db.EmbeddedDocumentField(UserDetails, required=True)
    profile_picture = db.URLField(default=True, null=True)
    contacts: Contacts = db.EmbeddedDocumentField(Contacts, required=True, default=Contacts)
    signup_date = db.DateTimeField(required=True, default=lambda: datetime.utcnow())
    last_login = db.DateTimeField(null=True)

    # balance
    balance: Balance = db.EmbeddedDocumentField(Balance, required=True, default=Balance)


    def clean(self):
        # if password field is a string, hash it before saving
        if isinstance(self.password, str):
            self.password = bcrypt.hashpw(self.password.encode('utf8'), bcrypt.gensalt())

    def validate(self, clean=True):
        super().validate(clean)
        if not self.phone_number:
            raise db.errors.ValidationError('Phone number is required')

    def check_password(self, input_password: str) -> bool:
        if not self.phone_number:
            raise ValueError('Phone number is required')
        
        return bcrypt.checkpw(input_password.encode('utf8'), self.password)

    def topup_balance(self, amount: int):
        # method shall not be called on unsaved/modified objects
        if self._get_changed_fields():
            raise db.errors.OperationError
        if amount <= 0:
            raise ValueError('Invalid amount for topup_balance()')

        modified = self.modify(inc__balance__amount=amount, set__balance__last_topup=datetime.utcnow())

        if not modified:
            raise db.errors.OperationError

    def spend_balance(self, amount: int):
        if self._get_changed_fields():
            raise db.errors.OperationError
        if amount <= 0:
            raise ValueError('Invalid amount for spend_balance()')

        modified = self.modify(inc__balance__amount=-amount)
        
        if not modified:
            raise db.errors.OperationError
