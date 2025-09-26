from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
from ..models import db, ServiceType, Citizen, Queue
from ..queue_logic.simple_optimizer import simple_optimizer
from ..utils.message_manager import get_message, get_error_response, get_success_response
from ..extensions import csrf
import uuid

# Blueprint is imported from __init__.py
from . import kiosk_bp

@kiosk_bp.route('/')
@kiosk_bp.route('/welcome')
def welcome():
    """Kiosk welcome screen - main entry point for citizens"""
    return render_template('kiosk_welcome.html', title='Welcome - CNI Digital Queue')

@kiosk_bp.route('/language/<lang>')
def set_language(lang):
    """Set the language preference for the kiosk session"""
    if lang in ['fr', 'en']:
        session['language'] = lang
        return jsonify({'success': True, 'language': lang})
    return jsonify({'success': False, 'message': 'Invalid language'}), 400

@kiosk_bp.route('/services')
def select_service():
    """Service selection screen"""
    language = session.get('language', 'fr')
    
    # Define ONLY core CNI services that are currently being worked on
    # These are the services citizens can actually complete at the center
    active_cni_service_codes = ['COLLECTION', 'RENEWAL', 'NEW_APP', 'CORRECTION']
    
    # Get only active CNI services that are currently operational
    cni_services = ServiceType.query.filter(
        ServiceType.is_active == True,
        ServiceType.code.in_(active_cni_service_codes)
    ).all()
    
    # Sort CNI services by priority (Collection first as quickest, Correction last as most complex)
    priority_order = ['COLLECTION', 'RENEWAL', 'NEW_APP', 'CORRECTION']
    cni_services.sort(key=lambda x: priority_order.index(x.code) if x.code in priority_order else 999)
    
    # Only show currently operational CNI services
    ordered_services = cni_services
    
    services_data = []
    for service in ordered_services:
        services_data.append({
            'id': service.id,
            'code': service.code,
            'name': service.name_fr if language == 'fr' else service.name_en,
            'description': service.description_fr if language == 'fr' else service.description_en,
            'estimated_duration': service.estimated_duration,
            'priority_level': service.priority_level,
            'is_cni_service': True  # All services shown are CNI services now
        })
    
    return render_template('kiosk_services.html', 
                         title='Select Service - CNI Digital Queue',
                         services=services_data,
                         language=language)

@kiosk_bp.route('/checkin')
def checkin_form():
    """Check-in form for pre-enrollment code entry"""
    service_id = request.args.get('service_id')
    language = session.get('language', 'fr')
    
    if not service_id:
        return jsonify({'error': 'Service ID required'}), 400
    
    service = ServiceType.query.get_or_404(service_id)
    service_data = {
        'id': service.id,
        'name': service.name_fr if language == 'fr' else service.name_en,
        'estimated_duration': service.estimated_duration
    }
    
    return render_template('kiosk_checkin.html',
                         title='Check-in - CNI Digital Queue',
                         service=service_data,
                         language=language)

@kiosk_bp.route('/process-checkin', methods=['POST'])
@csrf.exempt
def process_checkin():
    """Process citizen check-in and generate ticket"""
    try:
        data = request.get_json()
        
        pre_enrollment_code = data.get('pre_enrollment_code', '').strip()
        service_type_id = data.get('service_type_id')
        
        # Get service type first
        service_type = ServiceType.query.get(service_type_id)
        if not service_type:
            language = session.get('language', 'fr')
            return jsonify(get_error_response('invalid_service_type', language))
        
        # Services that require pre-enrollment codes
        services_requiring_code = ['RENEWAL', 'COLLECTION', 'CORRECTION']
        
        citizen = None
        if service_type.code in services_requiring_code:
            # Validate pre-enrollment code for services that require it
            if not pre_enrollment_code:
                language = session.get('language', 'fr')
                return jsonify(get_error_response('pre_enrollment_required', language))
            
            citizen = Citizen.query.filter_by(pre_enrollment_code=pre_enrollment_code).first()
            if not citizen:
                language = session.get('language', 'fr')
                return jsonify(get_error_response('invalid_pre_enrollment_code', language))
        else:
            # For services that don't require pre-enrollment (NEW_APP, EMERGENCY)
            if pre_enrollment_code:
                # If code provided, validate it
                citizen = Citizen.query.filter_by(pre_enrollment_code=pre_enrollment_code).first()
                if not citizen:
                    language = session.get('language', 'fr')
                    return jsonify(get_error_response('invalid_pre_enrollment_code', language))
            else:
                # Create temporary citizen record for walk-in services
                import uuid
                temp_code = f"TEMP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
                citizen = Citizen(
                    pre_enrollment_code=temp_code,
                    first_name="Walk-in",
                    last_name="Citizen",
                    date_of_birth=datetime.now().date(),
                    preferred_language=session.get('language', 'fr')
                )
                db.session.add(citizen)
                db.session.flush()  # Get the ID without committing
        
        # Check if citizen already has an active ticket
        existing_ticket = Queue.query.filter_by(
            citizen_id=citizen.id,
            status='waiting'
        ).first()
        
        if existing_ticket:
            language = session.get('language', 'fr')
            message = 'Vous avez déjà un ticket actif' if language == 'fr' else 'You already have an active ticket'
            return jsonify({
                'success': True,
                'ticket_number': existing_ticket.ticket_number,
                'service_name': service_type.name_fr if language == 'fr' else service_type.name_en,
                'estimated_wait': service_type.estimated_duration,
                'message': message,
                'redirect_to_ticket': True
            })
        
        # Generate memorable ticket number with service abbreviation
        service_abbreviations = {
            'NEW_APP': 'NA',
            'RENEWAL': 'RN', 
            'COLLECTION': 'CO',  # Fixed: Changed from 'CL' to 'CO' per documentation
            'CORRECTION': 'CR',
            'EMERGENCY': 'EM'
        }
        
        # Get service abbreviation or use first 2 letters of service code
        service_abbrev = service_abbreviations.get(service_type.code, service_type.code[:2])
        
        # Generate sequence number (4 digits) with uniqueness guard
        import random
        max_attempts = 5
        ticket_number = None
        for _ in range(max_attempts):
            sequence = random.randint(1000, 9999)
            candidate = f"{service_abbrev}{sequence}"
            # Check uniqueness
            if not Queue.query.filter_by(ticket_number=candidate).first():
                ticket_number = candidate
                break
        if not ticket_number:
            # Fallback to a UUID-based ticket number to guarantee uniqueness
            ticket_number = f"{service_abbrev}{uuid.uuid4().hex[:6].upper()}"
        
        # Calculate priority score using simplified calculator
        special_factors = {}
        if citizen.special_needs:
            special_needs_lower = citizen.special_needs.lower()
            if 'elderly' in special_needs_lower:
                special_factors['elderly'] = True
            if 'disability' in special_needs_lower:
                special_factors['disability'] = True
            if 'pregnant' in special_needs_lower:
                special_factors['pregnant'] = True
            if 'appointment' in special_needs_lower:
                special_factors['appointment'] = True
        
        priority_score = simple_optimizer.priority_calculator.calculate_priority_score(
            citizen, service_type, 0, special_factors  # 0 wait time for new tickets
        )
        
        # Create ticket
        ticket = Queue(
            ticket_number=ticket_number,
            citizen_id=citizen.id,
            service_type_id=service_type_id,
            status='waiting',
            priority_score=priority_score
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ticket_number': ticket.ticket_number,
            'service_name': service_type.name_fr if session.get('language') == 'fr' else service_type.name_en,
            'estimated_wait': service_type.estimated_duration
        })
        
    except Exception as e:
        db.session.rollback()
        language = session.get('language', 'fr')
        return jsonify(get_error_response('ticket_generation_error', language, 500))

@kiosk_bp.route('/ticket/<ticket_number>')
def show_ticket(ticket_number):
    """Display ticket information and queue status"""
    try:
        # Get ticket
        ticket = Queue.query.filter_by(ticket_number=ticket_number).first()
        if not ticket:
            language = session.get('language', 'fr')
            return render_template('kiosk_error.html', 
                                 error_message=get_message('ticket_not_found', language),
                                 title='Error - CNI Digital Queue',
                                 language=language)
        
        # Get citizen and service information
        citizen = ticket.citizen
        service_type = ticket.service_type
        language = session.get('language', 'fr')
        
        # Calculate current queue position (lower priority_score = higher priority)
        current_position = Queue.query.filter(
            Queue.service_type_id == service_type.id,
            Queue.status == 'waiting',
            Queue.priority_score <= ticket.priority_score,
            Queue.created_at <= ticket.created_at
        ).count()
        
        # Calculate estimated wait time
        estimated_wait = max(0, (current_position - 1) * service_type.estimated_duration)
        
        ticket_info = {
            'ticket_number': ticket_number,
            'service_name': service_type.name_fr if language == 'fr' else service_type.name_en,
            'queue_position': current_position,
            'estimated_wait_time': estimated_wait,
            'status': ticket.status,
            'created_at': ticket.created_at.strftime('%H:%M')
        }
        
        return render_template('kiosk_ticket.html', 
                             ticket=ticket_info, 
                             language=language,
                             title='Ticket - CNI Digital Queue')
        
    except Exception as e:
        language = session.get('language', 'fr')
        return render_template('kiosk_error.html', 
                             error_message=get_message('system_error', language),
                             title='Error - CNI Digital Queue',
                             language=language)

@kiosk_bp.route('/status')
def system_status():
    """Display current system status and queue information"""
    language = session.get('language', 'fr')
    
    # Get current queue statistics
    total_waiting = Queue.query.filter_by(status='waiting').count()
    total_in_progress = Queue.query.filter_by(status='in_progress').count()
    
    # Get service-wise queue counts
    services_status = []
    active_services = ServiceType.query.filter_by(is_active=True).all()
    
    for service in active_services:
        waiting_count = Queue.query.filter(
            Queue.service_type_id == service.id,
            Queue.status == 'waiting'
        ).count()
        
        services_status.append({
            'name': service.name_fr if language == 'fr' else service.name_en,
            'waiting_count': waiting_count,
            'estimated_duration': service.estimated_duration
        })
    
    status_data = {
        'total_waiting': total_waiting,
        'total_in_progress': total_in_progress,
        'services': services_status,
        'last_updated': datetime.now().strftime('%H:%M:%S')
    }
    
    return render_template('kiosk_status.html',
                         title='System Status - CNI Digital Queue',
                         status=status_data,
                         language=language)