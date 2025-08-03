import os
from datetime import datetime, timedelta
import pika

from app.utils.helpers import str_to_bool

basedir = os.path.abspath(os.path.dirname(__file__))


EVENT_TYPES = ['a-simple-event', 'a-complex-event']


class Config(object):
    # application environment (development/production)
    # NOTE: replaces FLASK_ENV which was deprecated in Flask 2.2
    #       WEBAPP_ENV relaxes some of the security settings in development mode, hence the default is production
    WEBAPP_ENV = os.getenv('WEBAPP_ENV', 'production')
    assert WEBAPP_ENV in ['development', 'production']
    
    # celery configs
    CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']
    CELERY_RESULT_BACKEND = os.environ['CELERY_RESULT_BACKEND']
    CELERY_IMPORTS = ('app.tasks',)

    # celery queues
    REPORT_CELERY_QUEUE = os.environ['REPORT_CELERY_QUEUE']

    # application database - MongoDB
    # PyMongo config
    MONGODB_URI = os.environ['MONGODB_URI']
    # Flask-MongoEngine config
    MONGODB_SETTINGS = {
        'HOST': MONGODB_URI,
        'DB': 'webapp',
        'CONNECT': False
    }

    # JWT sessions database - Redis
    REDIS_EVENTS_URL = os.environ['REDIS_EVENTS_URL']

    # RabbitMQ (flask-pika) for order handler communication
    FLASK_PIKA_PARAMS = pika.ConnectionParameters(
        host=os.environ['FLASK_PIKA_HOST'],
        credentials=pika.PlainCredentials(
            username=os.environ['FLASK_PIKA_USERNAME'],
            password=os.environ['FLASK_PIKA_PASSWORD']
        ) if os.environ.get('FLASK_PIKA_USERNAME', None) else pika.ConnectionParameters._DEFAULT
    )

    # media bucket (S3)
    MEDIA_BUCKET_ACCESS_KEY = os.environ['MEDIA_BUCKET_ACCESS_KEY']
    MEDIA_BUCKET_ACCESS_SECRET = os.environ['MEDIA_BUCKET_ACCESS_SECRET']
    MEDIA_BUCKET_NAME = os.environ['MEDIA_BUCKET_NAME']
    MEDIA_BASE_URL = os.environ['MEDIA_BASE_URL']

    # JWT token settings
    JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']
    JWT_ALGORITHM = 'HS256'
    JWT_DECODE_ALGORITHMS = ['HS256']
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.environ['JWT_ACCESS_TOKEN_EXPIRES']))
    JWT_ACCESS_TOKEN_REFRESH = timedelta(hours=int(os.environ['JWT_ACCESS_TOKEN_REFRESH']))
    JWT_COOKIE_SECURE = str_to_bool(os.environ['JWT_COOKIE_SECURE'])
    # if JWT_COOKIE_CSRF_PROTECT true then set_refresh_cookies() also sets the non-httponly CSRF cookies
    JWT_COOKIE_CSRF_PROTECT = str_to_bool(os.environ['JWT_COOKIE_CSRF_PROTECT'])
    JWT_COOKIE_SAMESITE = 'None'
    JWT_COOKIE_MAX_AGE = 604800  # 7 days (seconds)
    JWT_SESSION_COOKIE = False
    JWT_CSRF_CHECK_FORM = True
    JWT_ACCESS_CSRF_HEADER_NAME = 'X-CSRF-TOKEN-ACCESS'
    JWT_REFRESH_CSRF_HEADER_NAME = 'X-CSRF-TOKEN-REFRESH'

    # other security configs
    CORS_HEADERS = 'Content-Type'

    JWT_COOKIE_DOMAIN = os.environ.get('JWT_COOKIE_DOMAIN')
    
    # ---------------------------------------------------------

    # view configs
    USERS_PAGE_SIZE = int(os.environ['USERS_PAGE_SIZE'])

    # media upload config
    MEDIA_ALLOWED_EXTENSIONS = ['.png']
    MEDIA_ALLOWED_MIMETYPES = ['image/png']
    MEDIA_MAX_SIZE = 500 * 1024  # 500 kB

    # user profile picture
    PROFILE_PIC_ALLOWED_EXTENSIONS = ['.jpeg', '.jpg', '.png']
    PROFILE_PIC_ALLOWED_MIMETYPES = ['image/jpeg', 'image/png']
    PROFILE_PIC_MAX_SIZE = 200 * 1024  # 200 kB

    # ---------------------------------------------------------

    # private helper members - should not be used outside of Config object
    __DEV = WEBAPP_ENV == 'development'
    __SOME_DEV_SETTING = str_to_bool(os.environ['SOME_DEV_SETTING'])
    SOME_DEV_SETTING = __SOME_DEV_SETTING if __DEV else False

    # API Docs for DEV environment (Swagger)
    SWAGGER_API_HOST = os.environ['SWAGGER_API_HOST']
    SWAGGER_BASE_PREFIX = "/docs"
    SWAGGER = {
        "swagger": "2.0",
        "openapi": "3.0.2",
        'uiversion': 3,
        "info": {
            "title": "Generic Flask WebApp API",
            "description": "API for Generic Flask web application",
            "version": "0.0.1"
        },
        "static_url_path": "/flasgger_static",
        "url_prefix": SWAGGER_BASE_PREFIX,
        # "static_folder": "static",  # must be set by user
        "swagger_ui": True if __DEV else False,
        "specs_route": "/",
        "host": SWAGGER_API_HOST,
        "schemes": ['http'] if SWAGGER_API_HOST.split(':')[0] == 'localhost' else ['https'],
    }
