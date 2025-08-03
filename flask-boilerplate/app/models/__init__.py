from app.models.another_model import AnotherModel
from app.models.report import Report
from app.models.user import User

# MongoEngine field options are sometimes counter-intuitive and not well documented
# Here a combination of options and the resulting behavior is documented for future reference
#
# *** Simple Fields (StringField, IntField, etc.) ***
#
#   + A field that has a default value and is always saved to the DB *
#         field = db.DateTimeField(required=True, default=lambda: datetime.utcnow()) OR
#         field = db.IntField(required=True, default=0)
#
#   + A field that can also be None and is always saved to the DB:
#         field = db.StringField(default=True, null=True)
#     The default=True value tricks MongoEngine into saving the field to the DB even if it's None
#
#     What DOES NOT work:
#     - StringField(default=None, null=True)
#         The field can take any value or be `null`. However, when `null`, it is not saved into the database
#     - StringField(required=True, null=True)
#         The field is required and a validation exception is raised when it is `null`
#
# *** Embedded Documents ***
#
#   + An embedded document that can be None or take any value and is always saved to the DB ***
#     By default, if not set, it's value is None
#         field = db.EmbeddedDocumentField(EmbeddedDoc, null=True)
#
#   + An embedded document that always exists in the DB and its embedded fields have default value ***
#         field = db.EmbeddedDocumentField(EmbeddedDoc, required=True, default=EmbeddedDoc)
#     Note that EmbeddedDoc must have a default value for all its fields for this to work
#     OR it must allow those fields to be None
#
