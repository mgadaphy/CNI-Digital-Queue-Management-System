
import pytest
from flask import template_rendered
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import create_app, db
from app.models import Agent, Queue, ServiceType, Citizen
from app.config import Config
from datetime import datetime, date

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def captured_templates(app):
    recorded = []
    def record(sender, template, context, **extra):
        recorded.append((template, context))
    template_rendered.connect(record, app)
    yield recorded
    template_rendered.disconnect(record, app)

def create_admin(app):
    with app.app_context():
        # Check if exists first to avoid double creation if test re-runs
        if Agent.query.filter_by(employee_id="ADMIN001").first():
            return
            
        admin = Agent(
            employee_id="ADMIN001",
            first_name="Admin",
            last_name="User",
            role="admin",
            is_active=True,
            status="available"
        )
        admin.email = "admin@test.com"
        admin.set_password("password")
        db.session.add(admin)
        db.session.commit()

def create_agent(app):
    with app.app_context():
        if Agent.query.filter_by(employee_id="AGENT001").first():
             agent = Agent.query.filter_by(employee_id="AGENT001").first()
             return agent.id

        agent = Agent(
            employee_id="AGENT001",
            first_name="Regular",
            last_name="Agent",
            role="agent",
            is_active=True,
            status="available"
        )
        agent.email = "agent@test.com"
        agent.set_password("password")
        db.session.add(agent)
        db.session.commit()
        return agent.id

def login(client, employee_id, password):
    return client.post('/auth/login', json=dict(
        employee_id=employee_id,
        password=password
    ), follow_redirects=True)

def test_manage_queue_name_error_fix(client, app, captured_templates):
    create_admin(app)
    login(client, 'ADMIN001', 'password')
    
    response = client.get('/admin/manage_queue')
    assert response.status_code == 200
    
    if captured_templates:
        template, context = captured_templates[0]
        assert template.name == 'admin_queue.html'
        assert 'queue_stats' in context, "queue_stats missing from context"
        assert context['queue_stats'] is not None, "queue_stats is None"

def test_system_reports_undefined_error_fix(client, app, captured_templates):
    create_admin(app)
    login(client, 'ADMIN001', 'password')
    
    response = client.get('/admin/system_reports')
    assert response.status_code == 200
    
    if captured_templates:
        template, context = captured_templates[0]
        assert template.name == 'admin_reports.html'
        assert 'daily_stats' in context, "daily_stats missing from context"
        assert context['daily_stats'] is not None
        assert 'total_served' in context['daily_stats']

def test_assign_ticket_excludes_admin(client, app):
    create_admin(app) # id=1
    agent_id = create_agent(app) # id=2
    
    login(client, 'ADMIN001', 'password')
    
    with app.app_context():
        # Setup data
        citizen = Citizen(
            first_name="John", 
            last_name="Doe", 
            pre_enrollment_code="PE123", 
            email="john@example.com",
            date_of_birth=date(1990, 1, 1)  # Added DOB
        )
        service = ServiceType(code="TEST", name_fr="Test", name_en="Test", priority_level=1, estimated_duration=10)
        db.session.add(citizen)
        db.session.add(service)
        db.session.commit()
        
        ticket = Queue(
            ticket_number="A001",
            citizen_id=citizen.id,
            service_type_id=service.id,
            status="waiting"
        )
        db.session.add(ticket)
        db.session.commit()
        ticket_id = ticket.id

        # Make Agent busy/unavailable to test that it DOESN'T fallback to Admin
        # Or better: keep Admin 'available', make Agent 'busy'.
        # The auto-assigner looks for 'available' agents.
        # If I exclude 'admin', then with Admin=Available and Agent=Busy, 
        # it should find NO agents.
        # If I didn't exclude 'admin', it would find Admin.
        
        agent = Agent.query.get(agent_id)
        agent.status = 'busy'
        db.session.commit()
    
    # Run assignment (POST API)
    response = client.post(f'/admin/api/assign_ticket/{ticket_id}', json={})
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert data['error_code'] == 'NO_AVAILABLE_AGENTS'
