from datetime import datetime, date
import logging

from flask import Flask, make_response, jsonify, request, g as g_context
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from flask_jwt_extended import get_jwt_identity
from flask_mongoengine import MongoEngine
from flask_redis import FlaskRedis
from flask_pika import Pika
from flask_marshmallow import Marshmallow
from jsonschema import ValidationError
from flasgger import Swagger
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
import pymongo
from bson import ObjectId
from redis import Redis
import boto3
from celery import Celery
from flask_log_request_id import RequestID, current_request_id

from config import Config, EVENT_TYPES


logger = logging.getLogger(__name__)

db = MongoEngine()
mongo_client = pymongo.MongoClient(Config.MONGODB_URI, connect=False)
mongodb = mongo_client['webapp']

USERS_COLL: pymongo.collection.Collection = mongodb['users']
REPORTS_COLL: pymongo.collection.Collection = mongodb['reports']
ANOTHER_MODEL_COLL: pymongo.collection.Collection = mongodb['another_model']
ERRORS_COLL: pymongo.collection.Collection = mongodb['errors']

# Redis client for events
# NOTE: FlaskRedis exposes a Redis client instance, but it is not a subclass of Redis
#       FlaskRedis | Redis typing is used to let the IDE provide autocompletion for Redis methods
redis_client: FlaskRedis | Redis = FlaskRedis(decode_responses=True, config_prefix='REDIS_EVENTS')

# pika client for event communication
pika_client = Pika()

# boto3 S3 resource and buckets
boto_s3 = boto3.resource(
    service_name='s3',
    aws_access_key_id=Config.MEDIA_BUCKET_ACCESS_KEY,
    aws_secret_access_key=Config.MEDIA_BUCKET_ACCESS_SECRET,
    region_name='blr1',
    endpoint_url='https://aws-s3-endpoint.com',
)
MEDIA_BUCKET = boto_s3.Bucket(Config.MEDIA_BUCKET_NAME)

# using marshmallow to marshall a few JSON responses
ma = Marshmallow()

# Swagger for OpenAPI documentation
swagger = Swagger()

api_spec = APISpec(
    title="Flask Boilerplate",
    version="1.0.0",
    openapi_version="3.0.2",
    plugins=[MarshmallowPlugin()],
)


# instantiating a RequestID object to assign each request a unique ID for logging
request_id = RequestID()

celery = Celery(
    __name__,
    backend=Config.CELERY_RESULT_BACKEND,
    broker=Config.CELERY_BROKER_URL,
)
celery.autodiscover_tasks(packages=['app.tasks'])

# configuring queues for different tasks
celery_conf = {
    'task_routes': {
        'app.tasks.report.process_report': {'queue': Config.REPORT_CELERY_QUEUE},
    },
    'task_time_limit': 60 * 60  # seconds - 1 hour task time limit
}


def init_g_context():
    # add request timestamp information to the g_context
    # useful for having a consistent timestamp across the request lifecycle
    utc_now = datetime.utcnow()
    g_context.utc_now = utc_now

    # ensure current_user is always available, at worst None if not authenticated
    # when the user is logged in, a loader in flask_jwt_extended module will set this
    g_context.current_user = None


# after_request handler to append Application-User-Id and Application-Request-Id headers
def append_application_headers(response):
    user = g_context.current_user
    response.headers['Application-User-Id'] = user.id if user else 'unauthenticated'
    response.headers['Application-Request-Id'] = current_request_id()
    return response


# handle jsonschema validation error
def handle_bad_request(error):
    # log specific errors to mongodb for debug
    if isinstance(error.description, ValidationError):

        if request.endpoint in ['event.rabbitmq_event_post', 'event.redis_event_post']:
            ERRORS_COLL.insert_one({
                '_id': generate_unique_id(),
                'user': get_jwt_identity(),
                'user_agent': request.user_agent.string,
                'time': datetime.utcnow(),
                'endpoint': request.endpoint,
                'error': error.description.message
            })

        return make_response(
            jsonify({
                'msg': 'Bad Object',
                'schema_error': error.description.message
            }),
            400
        )

    # handle other "Bad Request"-errors
    return error


class CustomJSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(obj):
        # encode date/datetime objects to ISO format strings
        # MongoDB saves timestamps with millisecond precision, using timespec='milliseconds' for consistency
        if isinstance(obj, datetime):
            return obj.isoformat(timespec='milliseconds')
        if isinstance(obj, date):
            return obj.isoformat()
        return DefaultJSONProvider.default(obj)


def generate_unique_id():
    return str(ObjectId())


def init_celery(app):
    celery.conf.update(**celery_conf)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def setup_rabbitmq(app):
    """ Setup RabbitMQ exchanges, queues, and bindings """
    # get a channel from flask-pika
    channel = pika_client.channel()
    
    try:
        # declare the main events exchange
        channel.exchange_declare(exchange='events', exchange_type='topic', durable=True)
        
        # declare queues for each event type and bind them
        for event_type in EVENT_TYPES:
            queue_name = f'events.{event_type}'
            channel.queue_declare(queue=queue_name, durable=True)
            channel.queue_bind(exchange='events', queue=queue_name, routing_key=event_type)
        
        print('RabbitMQ infrastructure setup completed')
    
    except Exception as e:
        logger.error(f'Failed to setup RabbitMQ infrastructure: {str(e)}')
        raise

    finally:
        # return the channel to the pool
        pika_client.return_channel(channel)


def init_mongo_indexes():
    # indexes for users collection
    USERS_COLL.create_index('phone_number', background=True, unique=True)  # authentication lookup
    USERS_COLL.create_index('access_token', background=True, unique=True)  # webhook validation
    USERS_COLL.create_index('contacts.email.contact', background=True)  # fast lookup for email
    USERS_COLL.create_index('status', background=True)  # filter active/inactive users
    USERS_COLL.create_index('role', background=True)  # admin queries

    # indexes for reports collection
    REPORTS_COLL.create_index('user', background=True)
    REPORTS_COLL.create_index('task_id', background=True, unique=True)
    REPORTS_COLL.create_index('status', background=True)
    REPORTS_COLL.create_index('created_at', background=True)


def create_base_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # configure a custom JSON encoder to handle datetime objects
    app.json_provider_class = CustomJSONProvider
    app.json = app.json_provider_class(app)

    if Config.WEBAPP_ENV == 'development':
        cors = CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"], }}, supports_credentials=True)

    from app.jwt import jwt

    db.init_app(app)
    redis_client.init_app(app)
    jwt.init_app(app)
    ma.init_app(app)

    request_id = RequestID(app)  # NOTE: this line is a workaround for an unfixed bug in init_app() that breaks
    # request_id.init_app(app)   #       lazy initialization pattern (see issue #50 on project GitHub)

    app.before_request(init_g_context)
    app.after_request(append_application_headers)
    app.register_error_handler(400, handle_bad_request)

    return app


def create_app(config_class=Config):
    app = create_base_app(config_class)

    pika_client.init_app(app)
    app.config['FLASK_PIKA_PARAMS'] = Config.FLASK_PIKA_PARAMS
    
    init_celery(app)
    setup_rabbitmq(app)

    # dev tools for development environment (API specs, schema routes and Swagger Web UI)
    if app.config['WEBAPP_ENV'] == 'development':
        swagger.init_app(app)

        from app.devtools import bp as devtools_blueprint
        app.register_blueprint(devtools_blueprint, url_prefix=Config.SWAGGER_BASE_PREFIX)

    from app import domains

    app.register_blueprint(domains.admin_blueprint, url_prefix='/admin')
    app.register_blueprint(domains.event_blueprint, url_prefix='/')
    app.register_blueprint(domains.auth_blueprint, url_prefix='/')
    app.register_blueprint(domains.report_blueprint, url_prefix='/')
    app.register_blueprint(domains.user_blueprint, url_prefix='/')
    app.register_blueprint(domains.webhook_blueprint, url_prefix='/webhook')

    return app
