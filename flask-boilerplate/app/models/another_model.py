import mongoengine as db
from mongoengine import EmbeddedDocument, queryset_manager
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List

from app.models.base_document import BaseDocument


class StatusEnum(str, Enum):
    DRAFT = 'draft'
    ACTIVE = 'active'
    ARCHIVED = 'archived'


# Embedded document example
class Settings(EmbeddedDocument):
    """Example embedded document with validation"""
    notifications_enabled = db.BooleanField(default=True)
    theme = db.StringField(default='light', choices=['light', 'dark'])
    
    def clean(self):
        """Custom validation example"""
        if not self.notifications_enabled and self.theme == 'dark':
            raise db.ValidationError('Dark theme requires notifications')


class AnotherModel(BaseDocument):    
    meta = {
        'collection': 'another_model',
        'ordering': ['-created_at']
    }

    name = db.StringField(required=True, max_length=150)
    description = db.StringField(max_length=500)
    
    status = db.EnumField(StatusEnum, required=True, default=StatusEnum.DRAFT)
    is_active = db.BooleanField(default=True)
    
    priority = db.IntField(min_value=1, max_value=10, default=5)
    price = db.DecimalField(min_value=0, precision=2, default=Decimal('0.00'))
    
    created_at = db.DateTimeField(required=True, default=lambda: datetime.utcnow())
    updated_at = db.DateTimeField(default=lambda: datetime.utcnow())
    published_at = db.DateTimeField()  # Used to demonstrate partial loading safety
    
    tags = db.ListField(db.StringField(max_length=30), default=list)    
    metadata = db.DictField(default=dict)    
    settings = db.EmbeddedDocumentField(Settings, default=Settings)    
    creator = db.StringField()  # Reference to User document ID    
    email = db.EmailField()  # Built-in email validation
    website = db.URLField()  # Built-in URL validation

    @queryset_manager
    def active_objects(cls, queryset):
        """Return only active, non-archived items"""
        return queryset.filter(is_active=True, status__ne=StatusEnum.ARCHIVED)

    def clean(self):
        """Custom validation logic"""
        super().clean()
        
        if self.status == StatusEnum.ACTIVE and not self.published_at:
            self.published_at = datetime.utcnow()
            
        if self.price and self.price < 0:
            raise db.ValidationError('Price cannot be negative')

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"AnotherModel(name='{self.name}', status='{self.status}')"

    @classmethod
    def search_by_tags(cls, tags: List[str]):
        """Search documents by tags"""
        return cls.objects.filter(tags__in=tags, is_active=True)

    def add_tag(self, tag: str):
        """Add a tag if it doesn't exist"""
        if tag and tag not in self.tags:
            self.tags.append(tag)
            self.save()
    
    def activate(self):
        # Field was loaded or this is a new document
        if not self.published_at:
            self.published_at = datetime.utcnow()
                
        self.status = StatusEnum.ACTIVE
        self.is_active = True
        self.save()
