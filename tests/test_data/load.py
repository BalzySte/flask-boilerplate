import os
import mongoengine

from tests.conftest import load_collections
from app import mongodb
from config import Config


if __name__ == '__main__':
    script_dir = os.path.abspath(os.path.dirname(__file__))
    data_path = os.path.join(script_dir, 'mongo_collections')

    # initialize MongoEngine connection

    mongoengine.connect(host=Config.MONGODB_URI)

    load_collections(mongodb, data_path)
