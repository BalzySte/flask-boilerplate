from datetime import datetime
from mongoengine import StringField, DateTimeField, DictField

from app.models.base_document import BaseDocument
from app.models.user import User


class Report(BaseDocument):
    """
    Simple report model for boilerplate demonstration.
    Stores async task results and processing status.
    """
    
    user = StringField(required=True)
    task_id = StringField(required=True)
    status = StringField(
        required=True, 
        choices=['pending', 'running', 'completed', 'failed'],
        default='pending'
    )
    
    created_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()
    
    result_data = DictField()
    error_message = StringField()
