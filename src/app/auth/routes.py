from flask import request, jsonify, render_template
from . import auth_bp
from ..models import Agent
from ..extensions import db, csrf
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
from flask_login import login_user
from werkzeug.security import check_password_hash

@auth_bp.route('/login', methods=['POST'])
@csrf.exempt
def login():
    data = request.get_json()
    employee_id = data.get('employee_id')
    password = data.get('password')
    
    if not employee_id or not password:
        return jsonify({'message': 'Employee ID and password are required'}), 400
    
    agent = Agent.query.filter_by(employee_id=employee_id).first()
    
    if not agent or not check_password_hash(agent.password_hash, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    # Log in the user with Flask-Login
    login_user(agent)
    
    access_token = create_access_token(identity=str(agent.id))
    response = jsonify({
        'message': 'Login successful',
        'agent': {
            'id': agent.id,
            'employee_id': agent.employee_id,
            'email': agent.email,
            'first_name': agent.first_name,
            'last_name': agent.last_name,
            'role': agent.role
        }
    })
    set_access_cookies(response, access_token)
    return response

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    employee_id = data.get('employee_id')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'agent')  # Default to 'agent', allow 'admin'

    if Agent.query.filter((Agent.employee_id == employee_id) | (Agent.email == email)).first():
        return jsonify({'message': 'Agent already exists'}), 409

    new_agent = Agent(
        employee_id=employee_id,
        email=email,
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        role=role
    )
    new_agent.set_password(password)
    db.session.add(new_agent)
    db.session.commit()

    return jsonify({'message': 'Agent registered successfully'}), 201

@auth_bp.route('/login-page', methods=['GET'])
def login_page():
    """Serve a simple login page"""
    return render_template('simple_login.html')

@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = jsonify({'message': 'Logout successful'})
    unset_jwt_cookies(response)
    return response

@auth_bp.route('/create-admin', methods=['POST'])
@csrf.exempt
def create_admin():
    """Create a test admin user for demo purposes"""
    try:
        # Check if admin already exists
        existing_admin = Agent.query.filter_by(employee_id='ADMIN001').first()
        if existing_admin:
            return jsonify({'message': 'Admin user already exists'}), 409
        
        admin_agent = Agent(
            employee_id='ADMIN001',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        # Set email using the property setter to handle encryption
        admin_agent.email = 'admin@cni.com'
        admin_agent.set_password('admin123')
        
        db.session.add(admin_agent)
        db.session.commit()
        
        return jsonify({'message': 'Admin user created successfully'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create admin user: {str(e)}'}), 400
