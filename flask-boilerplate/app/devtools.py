import logging

from flask import Blueprint
from flask import jsonify
from flask import send_file

from app import api_spec


bp = Blueprint('devtools', 'devtools')
logger = logging.getLogger(__name__)


@bp.route('/schemas/<filename>', methods=['GET'])
def get_json_schema(filename):
    """ Exposes JSON schemas for development """

    # filepath = 'app/schemas/' + filename
    filepath = 'schemas/' + filename

    # serve the content of the JSON schema file as file
    return send_file(filepath, as_attachment=True, mimetype='application/json')


@bp.route('/response-schemas/<model>', methods=['GET'])
def get_response_schema(model):
    """ Exposes response schemas for development """

    schema = api_spec.components.schemas.get(model)

    if not schema:
        return jsonify(f'Schema for model {model} not found'), 404

    return jsonify(schema)
