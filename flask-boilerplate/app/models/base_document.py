import mongoengine as db
from bson import ObjectId


def generate_unique_id():
    return str(ObjectId())


class BaseDocument(db.Document):
    DoesNotExist: db.DoesNotExist
    meta = {
        'abstract': True,
    }

    _id = db.StringField(primary_key=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if '_id' not in kwargs:
            self._id = generate_unique_id()
