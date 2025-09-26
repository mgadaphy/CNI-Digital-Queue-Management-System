from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..models import db, Citizen, Queue, ServiceType
from ..utils.optimized_queries import query_optimizer
from ..queue_logic.optimizer import process_citizen_checkin
from ..queue_logic.hybrid_optimizer import HybridOptimizationEngine
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__, url_prefix='/user')
hybrid_engine = HybridOptimizationEngine()

@user_bp.route('/')
@user_bp.route('/dashboard')
def dashboard():
    """User dashboard showing ticket status and queue information"""
    enrollment_code = session.get('enrollment_code')
    
    if not enrollment_code:
        return redirect(url_for('user.login'))
    
    # Use optimized citizen lookup
    citizen = query_optimizer.citizen_queries.find_citizen_by_enrollment_code(enrollment_code)
    if not citizen:
        session.pop('enrollment_code', None)
        return redirect(url_for('user.login'))
    
    # Get active ticket (optimized)
    active_ticket = Queue.query.filter_by(
        citizen_id=citizen.id,
        status='waiting'
    ).first()
    
    # Get ticket history with optimized query
    ticket_history = query_optimizer.citizen_queries.get_citizen_ticket_history(citizen.id, limit=10)
    
    # Get queue statistics with optimized query
    stats = query_optimizer.queue_queries.get_queue_statistics()
    total_waiting = stats.get('queue', {}).get('waiting', 0)
    
    # Calculate estimated wait time if user has active ticket
    estimated_wait = None
    queue_position = None
    
    if active_ticket:
        # Use optimized queue position calculation
        position_data = query_optimizer.queue_queries.get_citizen_queue_position(
            citizen.id, active_ticket.id
        )
        queue_position = position_data.get('position')
        estimated_wait = position_data.get('estimated_wait_minutes')
    
    return render_template('user_dashboard.html',
                         citizen=citizen,
                         active_ticket=active_ticket,
                         ticket_history=ticket_history,
                         total_waiting=total_waiting,
                         estimated_wait=estimated_wait,
                         queue_position=queue_position)

@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login with enrollment code"""
    if request.method == 'POST':
        data = request.get_json()
        enrollment_code = data.get('enrollment_code', '').strip().upper()
        
        if not enrollment_code:
            return jsonify({'success': False, 'message': 'Enrollment code is required'}), 400
        
        citizen = Citizen.query.filter_by(pre_enrollment_code=enrollment_code).first()
        if not citizen:
            return jsonify({'success': False, 'message': 'Invalid enrollment code'}), 400
        
        session['enrollment_code'] = enrollment_code
        return jsonify({'success': True, 'redirect': url_for('user.dashboard')})
    
    return render_template('user_login.html')

@user_bp.route('/logout')
def logout():
    """User logout"""
    session.pop('enrollment_code', None)
    return redirect(url_for('user.login'))

@user_bp.route('/services')
def services():
    """Service selection for ticket generation"""
    enrollment_code = session.get('enrollment_code')
    
    if not enrollment_code:
        return redirect(url_for('user.login'))
    
    citizen = Citizen.query.filter_by(pre_enrollment_code=enrollment_code).first()
    if not citizen:
        return redirect(url_for('user.login'))
    
    # Check if user already has an active ticket
    active_ticket = Queue.query.filter_by(
        citizen_id=citizen.id,
        status='waiting'
    ).first()
    
    if active_ticket:
        return redirect(url_for('user.dashboard'))
    
    # Get available services
    services = ServiceType.query.filter_by(is_active=True).order_by(ServiceType.priority_level).all()
    
    return render_template('user_services.html',
                         citizen=citizen,
                         services=services)

@user_bp.route('/request-ticket', methods=['POST'])
def request_ticket():
    """Generate a new ticket for the user"""
    enrollment_code = session.get('enrollment_code')
    
    if not enrollment_code:
        return jsonify({'success': False, 'message': 'Please login first'}), 401
    
    citizen = Citizen.query.filter_by(pre_enrollment_code=enrollment_code).first()
    if not citizen:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    data = request.get_json()
    service_type_id = data.get('service_type_id')
    special_factors = data.get('special_factors', {})
    
    if not service_type_id:
        return jsonify({'success': False, 'message': 'Service type is required'}), 400
    
    service_type = ServiceType.query.get(service_type_id)
    if not service_type:
        return jsonify({'success': False, 'message': 'Invalid service type'}), 400
    
    # Check if user already has an active ticket
    existing_ticket = Queue.query.filter_by(
        citizen_id=citizen.id,
        status='waiting'
    ).first()
    
    if existing_ticket:
        return jsonify({
            'success': False, 
            'message': 'You already have an active ticket',
            'ticket_number': existing_ticket.ticket_number
        }), 400
    
    try:
        # Use hybrid optimization engine for ticket processing
        optimization_result = process_citizen_checkin(citizen, service_type, special_factors)
        
        # Generate ticket number
        service_abbreviations = {
            'NEW_APPLICATION': 'NA',
            'RENEWAL': 'RN', 
            'COLLECTION': 'CL',
            'CORRECTION': 'CR',
            'EMERGENCY': 'EM'
        }
        
        service_abbrev = service_abbreviations.get(service_type.code, service_type.code[:2])
        
        # Generate sequence number with uniqueness guard
        import random, uuid
        max_attempts = 5
        ticket_number = None
        for _ in range(max_attempts):
            sequence = random.randint(1000, 9999)
            candidate = f"{service_abbrev}{sequence}"
            if not Queue.query.filter_by(ticket_number=candidate).first():
                ticket_number = candidate
                break
        if not ticket_number:
            ticket_number = f"{service_abbrev}{uuid.uuid4().hex[:6].upper()}"
        
        # Create queue entry
        ticket = Queue(
            ticket_number=ticket_number,
            citizen_id=citizen.id,
            service_type_id=service_type_id,
            status='waiting',
            priority_score=optimization_result.priority_score,
            agent_id=optimization_result.recommended_agent_id
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        logger.info(f"Ticket {ticket_number} generated for citizen {citizen.id} with priority {optimization_result.priority_score}")
        
        return jsonify({
            'success': True,
            'ticket_number': ticket_number,
            'service_name': service_type.name_en,
            'estimated_wait_time': optimization_result.estimated_wait_time,
            'queue_position': optimization_result.queue_position,
            'priority_score': optimization_result.priority_score
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating ticket: {e}")
        return jsonify({'success': False, 'message': 'Error generating ticket'}), 500

@user_bp.route('/ticket-status/<ticket_number>')
def ticket_status(ticket_number):
    """Get current status of a ticket"""
    enrollment_code = session.get('enrollment_code')
    
    if not enrollment_code:
        return jsonify({'success': False, 'message': 'Please login first'}), 401
    
    citizen = Citizen.query.filter_by(pre_enrollment_code=enrollment_code).first()
    if not citizen:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    ticket = Queue.query.filter_by(
        ticket_number=ticket_number,
        citizen_id=citizen.id
    ).first()
    
    if not ticket:
        return jsonify({'success': False, 'message': 'Ticket not found'}), 404
    
    # Calculate current position if waiting
    queue_position = None
    estimated_wait = None
    
    if ticket.status == 'waiting':
        tickets_ahead = Queue.query.filter(
            Queue.status == 'waiting',
            Queue.priority_score > ticket.priority_score
        ).count()
        
        queue_position = tickets_ahead + 1
        estimated_wait = tickets_ahead * 5  # 5 minutes per person
    
    return jsonify({
        'success': True,
        'ticket': {
            'number': ticket.ticket_number,
            'status': ticket.status,
            'service_name': ticket.service_type.name_en,
            'created_at': ticket.created_at.isoformat(),
            'queue_position': queue_position,
            'estimated_wait': estimated_wait,
            'agent_id': ticket.agent_id,
            'called_at': ticket.called_at.isoformat() if ticket.called_at else None,
            'completed_at': ticket.completed_at.isoformat() if ticket.completed_at else None
        }
    })

@user_bp.route('/cancel-ticket/<ticket_number>', methods=['POST'])
def cancel_ticket(ticket_number):
    """Cancel an active ticket"""
    enrollment_code = session.get('enrollment_code')
    
    if not enrollment_code:
        return jsonify({'success': False, 'message': 'Please login first'}), 401
    
    citizen = Citizen.query.filter_by(pre_enrollment_code=enrollment_code).first()
    if not citizen:
        return jsonify({'success': False, 'message': 'Invalid session'}), 401
    
    ticket = Queue.query.filter_by(
        ticket_number=ticket_number,
        citizen_id=citizen.id,
        status='waiting'
    ).first()
    
    if not ticket:
        return jsonify({'success': False, 'message': 'Active ticket not found'}), 404
    
    try:
        ticket.status = 'cancelled'
        ticket.completed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Ticket {ticket_number} cancelled by citizen {citizen.id}")
        
        return jsonify({'success': True, 'message': 'Ticket cancelled successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cancelling ticket: {e}")
        return jsonify({'success': False, 'message': 'Error cancelling ticket'}), 500