from .extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy import Index
from .utils.encryption import encryption
from flask_login import UserMixin

class Citizen(db.Model):
    __tablename__ = 'citizens'
    id = db.Column(db.Integer, primary_key=True)
    pre_enrollment_code = db.Column(db.String(50), unique=True, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    _phone_number = db.Column('phone_number', db.String(255))  # Encrypted field
    _email = db.Column('email', db.String(255))  # Encrypted field
    preferred_language = db.Column(db.String(10), default='fr')
    special_needs = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def phone_number(self):
        """Decrypt and return phone number"""
        if self._phone_number:
            return encryption.decrypt_phone(self._phone_number)
        return None
    
    @phone_number.setter
    def phone_number(self, value):
        """Encrypt and store phone number"""
        if value:
            self._phone_number = encryption.encrypt_phone(value)
        else:
            self._phone_number = None
    
    @property
    def email(self):
        """Decrypt and return email"""
        if self._email:
            return encryption.decrypt(self._email)
        return None
    
    @email.setter
    def email(self, value):
        """Encrypt and store email"""
        if value:
            self._email = encryption.encrypt(value)
        else:
            self._email = None

class ServiceType(db.Model):
    __tablename__ = 'service_types'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name_fr = db.Column(db.String(100), nullable=False)
    name_en = db.Column(db.String(100), nullable=False)
    description_fr = db.Column(db.Text)
    description_en = db.Column(db.Text)
    priority_level = db.Column(db.Integer, nullable=False)
    estimated_duration = db.Column(db.Integer, nullable=False) # in minutes
    required_documents = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Station(db.Model):
    __tablename__ = 'stations'
    id = db.Column(db.Integer, primary_key=True)
    station_number = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    supported_services = db.Column(db.JSON)  # Array of service_type IDs
    is_active = db.Column(db.Boolean, default=True)
    location = db.Column(db.String(50))
    status = db.Column(db.String(20), default='available')  # available, serving, break, offline
    current_ticket = db.Column(db.String(20))  # Current ticket being served
    current_agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'))  # Current agent assigned
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = db.relationship('Agent', foreign_keys=[current_agent_id], backref='current_station')
    
    @property
    def queue_count(self):
        """Get current queue count for this station"""
        from sqlalchemy import func
        return db.session.query(func.count(Queue.id)).filter(
            Queue.station_id == self.id,
            Queue.status == 'waiting'
        ).scalar() or 0
    
    @property
    def avg_wait_time(self):
        """Get average wait time for this station"""
        from sqlalchemy import func
        result = db.session.query(func.avg(Queue.wait_time)).filter(
            Queue.station_id == self.id,
            Queue.status.in_(['completed', 'in_progress']),
            Queue.wait_time.isnot(None)
        ).scalar()
        return int(result) if result else None

class Agent(UserMixin, db.Model):
    __tablename__ = 'agents'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    _email = db.Column('email', db.String(255), unique=True, nullable=False)  # Encrypted field
    _phone = db.Column('phone', db.String(255))  # Encrypted field
    password_hash = db.Column(db.String(256))
    specializations = db.Column(db.JSON)  # Array of service_type IDs
    current_station_id = db.Column(db.Integer, db.ForeignKey('stations.id'))
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='offline') # offline, available, busy, break
    login_time = db.Column(db.DateTime)
    logout_time = db.Column(db.DateTime)
    role = db.Column(db.String(20), nullable=False, default='agent') # agent, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def email(self):
        """Decrypt and return email"""
        if self._email:
            return encryption.decrypt(self._email)
        return None
    
    @email.setter
    def email(self, value):
        """Encrypt and store email"""
        if value:
            self._email = encryption.encrypt(value)
        else:
            self._email = None
    
    @property
    def phone(self):
        """Decrypt and return phone number"""
        if self._phone:
            return encryption.decrypt_phone(self._phone)
        return None
    
    @phone.setter
    def phone(self, value):
        """Encrypt and store phone number"""
        if value:
            self._phone = encryption.encrypt_phone(value)
        else:
            self._phone = None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    # Flask-Login required methods
    def get_id(self):
        return str(self.id)

class Queue(db.Model):
    __tablename__ = 'queue'
    id = db.Column(db.Integer, primary_key=True)
    citizen_id = db.Column(db.Integer, db.ForeignKey('citizens.id'), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=False)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), default='waiting', nullable=False) # waiting, called, in_progress, completed, no_show
    priority_score = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    called_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    wait_time = db.Column(db.Integer)  # in minutes
    service_time = db.Column(db.Integer)  # in minutes
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'))
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'))

    citizen = db.relationship('Citizen', backref='queue_entries')
    service_type = db.relationship('ServiceType', backref='queue_entries')
    agent = db.relationship('Agent', backref='served_entries')
    station = db.relationship('Station', backref='served_entries')

# Audit and Logging Tables
class ServiceLog(db.Model):
    __tablename__ = 'service_logs'
    id = db.Column(db.Integer, primary_key=True)
    queue_entry_id = db.Column(db.Integer, db.ForeignKey('queue.id'), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    service_duration = db.Column(db.Integer)  # in minutes
    status = db.Column(db.String(20), nullable=False)  # completed, cancelled, transferred
    notes = db.Column(db.Text)
    citizen_satisfaction = db.Column(db.Integer)  # 1-5 rating
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    queue_entry = db.relationship('Queue', backref='service_logs')
    agent = db.relationship('Agent', backref='service_logs')
    service_type = db.relationship('ServiceType', backref='service_logs')
    station = db.relationship('Station', backref='service_logs')
    
    def __repr__(self):
        return f'<ServiceLog {self.id} - {self.status}>'

class SystemMetric(db.Model):
    __tablename__ = 'system_metrics'
    id = db.Column(db.Integer, primary_key=True)
    metric_type = db.Column(db.String(50), nullable=False)  # queue_length, wait_time, service_time, etc.
    metric_value = db.Column(db.Float, nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'))
    service_type_id = db.Column(db.Integer, db.ForeignKey('service_types.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    meta_data = db.Column(db.JSON)  # Additional context data
    
    # Relationships
    station = db.relationship('Station', backref='metrics')
    service_type = db.relationship('ServiceType', backref='metrics')
    
    def __repr__(self):
        return f'<SystemMetric {self.metric_type}: {self.metric_value}>'

class ErrorLog(db.Model):
    __tablename__ = 'error_logs'
    id = db.Column(db.Integer, primary_key=True)
    error_type = db.Column(db.String(50), nullable=False)
    error_message = db.Column(db.Text, nullable=False)
    stack_trace = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('agents.id'))
    endpoint = db.Column(db.String(200))
    request_data = db.Column(db.JSON)
    severity = db.Column(db.String(20), default='error')  # info, warning, error, critical
    resolved = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('Agent', backref='error_logs')
    
    def __repr__(self):
        return f'<ErrorLog {self.error_type} - {self.severity}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # login, logout, create_queue, update_status, etc.
    resource_type = db.Column(db.String(50))  # queue_entry, agent, station, etc.
    resource_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('Agent', backref='audit_logs')
    
    def __repr__(self):
        return f'<AuditLog {self.action} by {self.user_id}>'

# Performance Indexes
# Citizens table indexes
Index('idx_citizens_pre_enrollment_code', Citizen.pre_enrollment_code)
Index('idx_citizens_phone_number', Citizen._phone_number)
Index('idx_citizens_created_at', Citizen.created_at)

# Queue entries table indexes
Index('idx_queue_entries_status', Queue.status)
Index('idx_queue_entries_service_type', Queue.service_type_id)
Index('idx_queue_entries_created_at', Queue.created_at)
Index('idx_queue_entries_called_at', Queue.called_at)
Index('idx_queue_entries_completed_at', Queue.completed_at)
Index('idx_queue_entries_citizen_service', Queue.citizen_id, Queue.service_type_id)

# Agents table indexes
Index('idx_agents_employee_id', Agent.employee_id)
Index('idx_agents_email', Agent._email)
Index('idx_agents_status', Agent.status)
Index('idx_agents_station', Agent.current_station_id)
Index('idx_agents_active_status', Agent.is_active, Agent.status)

# Service logs table indexes
Index('idx_service_logs_queue_entry', ServiceLog.queue_entry_id)
Index('idx_service_logs_agent', ServiceLog.agent_id)
Index('idx_service_logs_service_type', ServiceLog.service_type_id)
Index('idx_service_logs_station', ServiceLog.station_id)
Index('idx_service_logs_start_time', ServiceLog.start_time)
Index('idx_service_logs_status', ServiceLog.status)

# System metrics table indexes
Index('idx_system_metrics_type_timestamp', SystemMetric.metric_type, SystemMetric.timestamp)
Index('idx_system_metrics_station_timestamp', SystemMetric.station_id, SystemMetric.timestamp)

# Error logs table indexes
Index('idx_error_logs_timestamp', ErrorLog.timestamp)
Index('idx_error_logs_severity', ErrorLog.severity)
Index('idx_error_logs_resolved', ErrorLog.resolved)

# Audit logs table indexes
Index('idx_audit_logs_user_timestamp', AuditLog.user_id, AuditLog.timestamp)
Index('idx_audit_logs_action', AuditLog.action)
Index('idx_audit_logs_resource', AuditLog.resource_type, AuditLog.resource_id)
