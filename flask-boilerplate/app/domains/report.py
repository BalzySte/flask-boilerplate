import logging

from flask import Blueprint, jsonify, request, g as g_context
from flask_jwt_extended import jwt_required
from flask_marshmallow.fields import fields as ma_fields

from app import ma, api_spec
from app.models import User, Report
from app.tasks.report import process_report

bp = Blueprint('report', 'report')
logger = logging.getLogger(__name__)


class ReportResponseSchema(ma.Schema):
    id = ma_fields.String(required=True, attribute='_id')
    task_id = ma_fields.String(required=True)
    user = ma_fields.String(required=True)
    status = ma_fields.String(required=True)
    created_at = ma_fields.DateTime(required=True)
    completed_at = ma_fields.DateTime(allow_none=True)
    result_data = ma_fields.Dict(allow_none=True)
    error_message = ma_fields.String(allow_none=True)


class ReportListItemSchema(ma.Schema):
    id = ma_fields.String(required=True, attribute='_id')
    task_id = ma_fields.String(required=True)
    status = ma_fields.String(required=True)
    created_at = ma_fields.DateTime(required=True)
    completed_at = ma_fields.DateTime(allow_none=True)


class ReportsListResponseSchema(ma.Schema):
    reports = ma_fields.List(ma_fields.Nested(ReportListItemSchema()), required=True)
    count = ma_fields.Integer(required=True)


report_response_schema = ReportResponseSchema()
reports_list_response_schema = ReportsListResponseSchema()

# add Marshmallow schemas to APISpec
api_spec.components.schema('ReportResponse', schema=ReportResponseSchema)
api_spec.components.schema('ReportsListResponse', schema=ReportsListResponseSchema)


@bp.route('/report', methods=['POST'])
@jwt_required()
def report_post():
    """Submit an async report generation task"""
    user: User = g_context.current_user
    
    # Create a new report record
    report = Report(
        user=user._id,  # Store user ID as string
        task_id='',  # Will be updated after task creation
        status='pending'
    )
    report.save()
    
    # Prepare task data
    task_data = {
        'user_id': user._id,
        'report_id': report._id
    }
    celery_kwargs = {}  # can specify queue and other task options here
    task = process_report.apply_async(args=[task_data], **celery_kwargs)
    
    # Update report with task_id
    report.task_id = task.task_id
    report.save()
    
    logger.info(f"Queued report task {task.task_id} for user {user._id}")
    
    return jsonify({
        'msg': 'report task submitted successfully',
        'report_id': report._id,
        'task_id': task.task_id
    }), 200


@bp.route('/report/<report_id>', methods=['GET'])
@jwt_required()
def report_get(report_id):
    """Get a specific report by ID"""
    user: User = g_context.current_user
    
    try:
        report: Report = Report.objects(_id=report_id, user=user._id).get()
    except Report.DoesNotExist:
        return jsonify({'msg': 'Report not found'}), 404
    
    return jsonify(report_response_schema.dump(report)), 200


@bp.route('/reports', methods=['GET'])
@jwt_required()
def reports_list():
    """List all reports for the current user"""
    user: User = g_context.current_user
    
    # Get query parameters
    status = request.args.get('status')
    limit = min(int(request.args.get('limit', 50)), 100)  # Max 100
    
    # Build query
    query = {'user': user._id}
    if status:
        query['status'] = status
    
    # Get reports
    reports = Report.objects(**query).order_by('-created_at').limit(limit)
    
    response_data = {
        'reports': list(reports),
        'count': len(reports)
    }
    
    return jsonify(reports_list_response_schema.dump(response_data)), 200
