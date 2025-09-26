from marshmallow import Schema, fields, validate, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from .models import Citizen, Queue, Agent, ServiceType, Station, ServiceLog, SystemMetric, ErrorLog, AuditLog
from .extensions import db
import re

# Base Schema with common validation
class BaseSchema(Schema):
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

# Citizen Schemas
class CitizenSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Citizen
        load_instance = True
        sqla_session = db.session
        include_fk = True
        exclude = ['id']
    
    # Use model field names directly
    pre_enrollment_code = fields.Str(required=True, validate=validate.Length(min=8, max=20))
    phone_number = fields.Str(validate=validate.Length(min=8, max=15))
    email = fields.Email(allow_none=True)
    
    @validates('pre_enrollment_code')
    def validate_pre_enrollment_code(self, value):
        # Basic validation for pre-enrollment code format
        if not re.match(r'^[A-Z0-9]+$', value):
            raise ValidationError('Pre-enrollment code must contain only alphanumeric characters')
    
    @validates('phone_number')
    def validate_phone_number(self, value):
        if value and not re.match(r'^\+?[0-9\s\-\(\)]+$', value):
            raise ValidationError('Invalid phone number format')

class CitizenCreateSchema(Schema):
    id_number = fields.Str(required=True, validate=validate.Length(min=8, max=20))
    first_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    phone = fields.Str(validate=validate.Length(min=8, max=15))
    email = fields.Email(allow_none=True)
    date_of_birth = fields.Date(allow_none=True)
    address = fields.Str(validate=validate.Length(max=500))

# Queue Entry Schemas
class QueueSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Queue
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    status = fields.Str(validate=validate.OneOf(['waiting', 'called', 'in_progress', 'completed', 'cancelled']))
    priority = fields.Int(validate=validate.Range(min=1, max=5))
    
class QueueEntryCreateSchema(Schema):
    citizen_id = fields.Int(required=True)
    service_type_id = fields.Int(required=True)
    priority = fields.Int(validate=validate.Range(min=1, max=5), missing=3)
    notes = fields.Str(validate=validate.Length(max=1000))

class QueueEntryUpdateSchema(Schema):
    status = fields.Str(validate=validate.OneOf(['waiting', 'called', 'in_progress', 'completed', 'cancelled']))
    agent_id = fields.Int(allow_none=True)
    station_id = fields.Int(allow_none=True)
    called_at = fields.DateTime(allow_none=True)
    completed_at = fields.DateTime(allow_none=True)
    notes = fields.Str(validate=validate.Length(max=1000))

# Agent Schemas
class AgentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Agent
        load_instance = True
        sqla_session = db.session
        include_fk = True
        exclude = ['password_hash']
    
    status = fields.Str(validate=validate.OneOf(['offline', 'available', 'busy', 'break']))
    role = fields.Str(validate=validate.OneOf(['agent', 'admin']))
    specializations = fields.List(fields.Int(), allow_none=True)

class AgentCreateSchema(Schema):
    employee_id = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    first_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    email = fields.Email(required=True)
    phone = fields.Str(validate=validate.Length(min=8, max=20))
    password = fields.Str(required=True, validate=validate.Length(min=8))
    role = fields.Str(validate=validate.OneOf(['agent', 'admin']), missing='agent')
    specializations = fields.List(fields.Int(), allow_none=True)
    current_station_id = fields.Int(allow_none=True)

class AgentUpdateSchema(Schema):
    first_name = fields.Str(validate=validate.Length(min=2, max=100))
    last_name = fields.Str(validate=validate.Length(min=2, max=100))
    email = fields.Email()
    phone = fields.Str(validate=validate.Length(min=8, max=20))
    status = fields.Str(validate=validate.OneOf(['offline', 'available', 'busy', 'break']))
    specializations = fields.List(fields.Int(), allow_none=True)
    current_station_id = fields.Int(allow_none=True)
    is_active = fields.Bool()

class AgentLoginSchema(Schema):
    employee_id = fields.Str(required=True)
    password = fields.Str(required=True)

# Service Type Schemas
class ServiceTypeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ServiceType
        load_instance = True
        sqla_session = db.session
    
    priority_level = fields.Int(validate=validate.Range(min=1, max=5))
    estimated_duration = fields.Int(validate=validate.Range(min=1, max=480))  # Max 8 hours
    required_documents = fields.List(fields.Str(), allow_none=True)

class ServiceTypeCreateSchema(Schema):
    code = fields.Str(required=True, validate=validate.Length(min=2, max=20))
    name_fr = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    name_en = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    description_fr = fields.Str(validate=validate.Length(max=1000))
    description_en = fields.Str(validate=validate.Length(max=1000))
    priority_level = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    estimated_duration = fields.Int(required=True, validate=validate.Range(min=1, max=480))
    required_documents = fields.List(fields.Str(), allow_none=True)

# Station Schemas
class StationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Station
        load_instance = True
        sqla_session = db.session
    
    supported_services = fields.List(fields.Int(), allow_none=True)

class StationCreateSchema(Schema):
    station_number = fields.Str(required=True, validate=validate.Length(min=1, max=10))
    name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    description = fields.Str(validate=validate.Length(max=500))
    location = fields.Str(validate=validate.Length(max=50))
    supported_services = fields.List(fields.Int(), allow_none=True)

# Service Log Schemas
class ServiceLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ServiceLog
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    status = fields.Str(validate=validate.OneOf(['completed', 'cancelled', 'transferred']))
    citizen_satisfaction = fields.Int(validate=validate.Range(min=1, max=5), allow_none=True)
    service_duration = fields.Int(validate=validate.Range(min=0, max=480))

class ServiceLogCreateSchema(Schema):
    queue_entry_id = fields.Int(required=True)
    agent_id = fields.Int(required=True)
    service_type_id = fields.Int(required=True)
    station_id = fields.Int(required=True)
    start_time = fields.DateTime(required=True)
    end_time = fields.DateTime(allow_none=True)
    status = fields.Str(required=True, validate=validate.OneOf(['completed', 'cancelled', 'transferred']))
    notes = fields.Str(validate=validate.Length(max=1000))
    citizen_satisfaction = fields.Int(validate=validate.Range(min=1, max=5), allow_none=True)

# System Metric Schemas
class SystemMetricSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = SystemMetric
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    metric_type = fields.Str(validate=validate.OneOf([
        'queue_length', 'wait_time', 'service_time', 'agent_utilization',
        'citizen_satisfaction', 'system_load', 'error_rate'
    ]))
    meta_data = fields.Dict(allow_none=True)

class SystemMetricCreateSchema(Schema):
    metric_type = fields.Str(required=True, validate=validate.OneOf([
        'queue_length', 'wait_time', 'service_time', 'agent_utilization',
        'citizen_satisfaction', 'system_load', 'error_rate'
    ]))
    metric_value = fields.Float(required=True)
    station_id = fields.Int(allow_none=True)
    service_type_id = fields.Int(allow_none=True)
    meta_data = fields.Dict(allow_none=True)

# Error Log Schemas
class ErrorLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ErrorLog
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    severity = fields.Str(validate=validate.OneOf(['info', 'warning', 'error', 'critical']))
    request_data = fields.Dict(allow_none=True)

class ErrorLogCreateSchema(Schema):
    error_type = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    error_message = fields.Str(required=True, validate=validate.Length(min=1, max=2000))
    stack_trace = fields.Str(validate=validate.Length(max=5000))
    user_id = fields.Int(allow_none=True)
    endpoint = fields.Str(validate=validate.Length(max=200))
    request_data = fields.Dict(allow_none=True)
    severity = fields.Str(validate=validate.OneOf(['info', 'warning', 'error', 'critical']), missing='error')

# Audit Log Schemas
class AuditLogSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = AuditLog
        load_instance = True
        sqla_session = db.session
        include_fk = True
    
    old_values = fields.Dict(allow_none=True)
    new_values = fields.Dict(allow_none=True)

class AuditLogCreateSchema(Schema):
    user_id = fields.Int(required=True)
    action = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    resource_type = fields.Str(validate=validate.Length(max=50))
    resource_id = fields.Int(allow_none=True)
    old_values = fields.Dict(allow_none=True)
    new_values = fields.Dict(allow_none=True)
    ip_address = fields.Str(validate=validate.Length(max=45))
    user_agent = fields.Str(validate=validate.Length(max=500))

# Response Schemas
class SuccessResponseSchema(Schema):
    success = fields.Bool(default=True)
    message = fields.Str()
    data = fields.Raw(allow_none=True)

class ErrorResponseSchema(Schema):
    success = fields.Bool(default=False)
    message = fields.Str(required=True)
    errors = fields.Dict(allow_none=True)
    error_code = fields.Str(allow_none=True)

# Pagination Schema
class PaginationSchema(Schema):
    page = fields.Int(validate=validate.Range(min=1), missing=1)
    per_page = fields.Int(validate=validate.Range(min=1, max=100), missing=20)
    sort_by = fields.Str(missing='created_at')
    sort_order = fields.Str(validate=validate.OneOf(['asc', 'desc']), missing='desc')

class PaginatedResponseSchema(Schema):
    items = fields.List(fields.Raw())
    total = fields.Int()
    pages = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
    has_next = fields.Bool()
    has_prev = fields.Bool()