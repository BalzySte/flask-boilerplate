import os
from bson.json_util import loads
import logging.config

import pytest
import pymongo


# add flask-boilerplate to Python path for all tests
# NOTE: marking flask-boilerplate as source root in the IDE also does the trick
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "flask-boilerplate"))


from app import create_app, init_mongo_indexes
from app import mongo_client, mongodb
from app.models import User
from flask import g


# simplified logging config for tests (applies both to webapp and celery)
# NOTE: this is necessary because the celery_worker provided by pytest shares the same logger as the webapp
#       and the webapp logger is configured with some filters that are not compatible with celery_worker
# configure logging
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'webapp': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'app': {
            'level': 'INFO',
            'handlers': ['webapp'],
            'propagate': True
        }
    }
})


@pytest.fixture(scope='session')
def flask_app():
    flask_app = create_app()

    # add post request handler to clean the g context
    # NOTE: this is necessary cause the test client (differently from the actual app) does not clean the g context
    #       see: https://github.com/pallets/flask/issues/2567
    @flask_app.teardown_request
    def clean_g_context(response):
        for key in list(iter(g)):
            g.pop(key, None)

    with flask_app.test_request_context():
        yield flask_app


@pytest.fixture(scope='session')
def test_client(flask_app):
    # Create a test client using the Flask application configured for testing
    yield flask_app.test_client()


# a separate test client used to test webhooks and other un-authenticated endpoints called by external services
@pytest.fixture(scope='session')
def webhook_test_client(flask_app):
    # Create a test client using the Flask application configured for testing
    yield flask_app.test_client()


@pytest.fixture(scope='module')
def init_database():
    # load mongodb test data
    script_dir = os.path.abspath(os.path.dirname(__file__))
    init_mongo_indexes()
    load_collections(mongodb, os.path.join(script_dir, 'test_data/mongo_collections'))
    yield
    mongo_client.drop_database('webapp')


@pytest.fixture(scope='session')
def celery_worker_parameters():
    return {
        'queues':  ('celery', 'report'),
        'shutdown_timeout': 10
    }


def pytest_sessionstart(session):
    mongo_client.drop_database('webapp')


def pytest_sessionfinish(session, exitstatus):
    mongo_client.drop_database('webapp')


def load_collections(mongo_database: pymongo.mongo_client.database.Database, backup_db_dir: str):
    files = os.listdir(backup_db_dir)
    for filename in files:

        # filename without extension is the collection name
        coll_name = filename.split('/')[-1].split('.')[0]
        with open(os.path.join(backup_db_dir, filename)) as file:
            json_string = file.read()
            coll_data = loads(json_string)

        # insert users collection through MongoEngine model (this populates all the necessary fields)
        if coll_name == 'users':
            for user_data in coll_data:
                u = User(**user_data)
                u.save()
            continue

        mongo_database[coll_name].insert_many(coll_data)
