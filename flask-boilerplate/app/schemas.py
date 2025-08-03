import json
from pathlib import Path


def load_schema(filename):
    # Get the directory containing this file, then navigate to schemas directory
    current_file = Path(__file__)
    schemas_dir = current_file.parent / 'schemas'
    file_path = schemas_dir / filename
    
    with open(file_path, 'rt') as file:
        schema = json.load(file)
    # replace $id prop with absolute path to the file
    # this allows jsonschema to locate  $ref URIs
    if '$id' in schema:
        schema['$id'] = 'file://' + str(schemas_dir.resolve() / schema['$id'])
    return schema


# auth schemas
schema_register = load_schema('register.json')
schema_register_confirm = load_schema('register_confirm.json')
schema_login = load_schema('login.json')

# user schemas
schema_user_put = load_schema('user_put.json')
schema_user_contacts_post = load_schema('user_contacts_post.json')

# webhook schemas
schema_webhook_alert_post = load_schema('webhook_alert_post.json')

# report schemas
schema_report_post = load_schema('report_post.json')
