from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from ..models import db, Agent, ServiceType, Station, Citizen, Queue
from ..queue_logic.hybrid_optimizer import HybridOptimizationEngine

agent_bp = Blueprint('agent', __name__, url_prefix='/agent')

@agent_bp.route('/dashboard')
@login_required
def agent_dashboard():
    """Agent dashboard with assigned tickets and queue management - FIXED VERSION"""
    
    agent = current_user
    
    # Simple approach - get assigned tickets directly
    assigned_tickets = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status.in_(['waiting', 'in_progress'])
    ).all()
    
    # Add wait time for each ticket
    for ticket in assigned_tickets:
        if ticket.created_at:
            wait_time = datetime.utcnow() - ticket.created_at
            hours, remainder = divmod(wait_time.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                ticket.wait_time_display = f"{int(hours)}h {int(minutes)}m"
            else:
                ticket.wait_time_display = f"{int(minutes)}m"
        else:
            ticket.wait_time_display = "N/A"
    
    # Get currently serving
    currently_serving = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status == 'in_progress'
    ).first()
    
    # Get next citizen (prefer waiting over in_progress)
    waiting_tickets = [t for t in assigned_tickets if t.status == 'waiting']
    in_progress_tickets = [t for t in assigned_tickets if t.status == 'in_progress']
    
    next_citizen = None
    if waiting_tickets:
        next_citizen = waiting_tickets[0]
    elif in_progress_tickets:
        next_citizen = in_progress_tickets[0]
    
    # Basic metrics
    today = datetime.utcnow().date()
    citizens_served_today = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status == 'completed',
        func.date(Queue.updated_at) == today
    ).count()
    
    metrics = {
        'citizens_served_today': citizens_served_today,
        'avg_service_time': 15
    }
    
    # General queue for overview
    queue_items = Queue.query.filter(
        Queue.status.in_(['waiting', 'in_progress'])
    ).join(Citizen).join(ServiceType).order_by(
        desc(Queue.priority_score), Queue.created_at
    ).limit(10).all()
    
    return render_template('agent_dashboard.html',
                         agent=agent,
                         metrics=metrics,
                         currently_serving=currently_serving,
                         assigned_tickets=assigned_tickets,
                         next_citizen=next_citizen,
                         queue_items=queue_items,
                         datetime=datetime)

@agent_bp.route('/call_next', methods=['POST'])
@login_required
def call_next():
    """Call next citizen in agent's assigned queue"""
    agent = current_user
    
    # Get next assigned ticket
    next_ticket = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status == 'waiting'
    ).order_by(desc(Queue.priority_score), Queue.created_at).first()
    
    if next_ticket:
        next_ticket.status = 'in_progress'
        next_ticket.updated_at = datetime.utcnow()
        agent.status = 'busy'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Now serving ticket {next_ticket.ticket_number}',
            'ticket': {
                'id': next_ticket.id,
                'ticket_number': next_ticket.ticket_number,
                'service_type': (next_ticket.service_type.name_en if next_ticket.service_type and next_ticket.service_type.name_en else next_ticket.service_type.name_fr)
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': 'No tickets assigned to you'
        }), 400

@agent_bp.route('/complete_service', methods=['POST'])
@login_required
def complete_service():
    """Complete current service"""
    try:
        agent = current_user
        
        # Handle both JSON and form data
        if request.is_json:
            ticket_id = request.json.get('ticket_id')
        else:
            ticket_id = request.form.get('ticket_id')
        
        if not ticket_id:
            return jsonify({
                'success': False,
                'message': 'No ticket ID provided'
            }), 400
        
        ticket = Queue.query.filter(
            Queue.id == ticket_id,
            Queue.agent_id == agent.id,
            Queue.status == 'in_progress'
        ).first()
        
        if ticket:
            ticket.status = 'completed'
            ticket.updated_at = datetime.utcnow()
            agent.status = 'available'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Service completed for ticket {ticket.ticket_number}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Ticket not found or not assigned to you'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error completing service: {e}")
        return jsonify({
            'success': False,
            'message': f'Error completing service: {str(e)}'
        }), 500

@agent_bp.route('/update_status', methods=['POST'])
@login_required
def update_status():
    """Update agent status"""
    agent = current_user
    new_status = request.json.get('status')
    
    valid_statuses = ['available', 'on_break', 'busy', 'offline']
    if new_status not in valid_statuses:
        return jsonify({
            'success': False,
            'message': 'Invalid status'
        }), 400
    
    agent.status = new_status
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Status updated to {new_status}'
    })

@agent_bp.route('/api/assigned_tickets')
@login_required
def get_assigned_tickets():
    """API endpoint to get agent's assigned tickets"""
    agent = current_user
    
    assigned_tickets = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status.in_(['waiting', 'in_progress'])
    ).join(Citizen).join(ServiceType).order_by(
        desc(Queue.priority_score), Queue.created_at
    ).all()
    
    tickets_data = []
    for ticket in assigned_tickets:
        if ticket.created_at:
            wait_time = datetime.utcnow() - ticket.created_at
            hours, remainder = divmod(wait_time.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                wait_time_display = f"{int(hours)}h {int(minutes)}m"
            else:
                wait_time_display = f"{int(minutes)}m"
        else:
            wait_time_display = "N/A"
            
        tickets_data.append({
            'id': ticket.id,
            'ticket_number': ticket.ticket_number,
            'citizen_name': f"{ticket.citizen.first_name} {ticket.citizen.last_name}",
            'service_name': (ticket.service_type.name_en if ticket.service_type and ticket.service_type.name_en else ticket.service_type.name_fr),
            'priority_score': ticket.priority_score,
            'status': ticket.status,
            'wait_time_display': wait_time_display,
            'created_at': ticket.created_at.isoformat() if ticket.created_at else None
        })
    
    return jsonify({'tickets': tickets_data})

@agent_bp.route('/api/queue_overview')
@login_required
def get_queue_overview():
    """API endpoint to get general queue overview"""
    
    queue_items = Queue.query.filter(
        Queue.status.in_(['waiting', 'in_progress'])
    ).join(Citizen).join(ServiceType).order_by(
        desc(Queue.priority_score), Queue.created_at
    ).limit(20).all()
    
    queue_data = []
    for item in queue_items:
        if item.created_at:
            wait_time = datetime.utcnow() - item.created_at
            minutes = int(wait_time.total_seconds() // 60)
        else:
            minutes = 0
            
        queue_data.append({
            'ticket_number': item.ticket_number,
            'service_type': (item.service_type.name_en if item.service_type and item.service_type.name_en else item.service_type.name_fr),
            'wait_time_minutes': minutes,
            'status': item.status,
            'assigned_agent': f"{item.agent.first_name} {item.agent.last_name}" if item.agent else None
        })
    
    return jsonify({'queue_items': queue_data})

@agent_bp.route('/api/status', methods=['PUT'])
@login_required
def update_agent_status():
    """Update agent status"""
    try:
        agent = current_user
        data = request.get_json()
        
        new_status = data.get('status')
        if new_status not in ['available', 'busy', 'on_break', 'offline']:
            return jsonify({
                'success': False,
                'message': 'Invalid status. Must be: available, busy, on_break, or offline'
            }), 400
        
        agent.status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Status updated to {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        }), 500

@agent_bp.route('/dashboard_fixed')
@login_required
def agent_dashboard_fixed():
    """FIXED Agent dashboard - bypasses caching issues"""
    
    agent = current_user
    
    # Simple approach - get assigned tickets directly
    assigned_tickets = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status.in_(['waiting', 'in_progress'])
    ).all()
    
    # Add wait time for each ticket
    for ticket in assigned_tickets:
        if ticket.created_at:
            wait_time = datetime.utcnow() - ticket.created_at
            hours, remainder = divmod(wait_time.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            if hours > 0:
                ticket.wait_time_display = f"{int(hours)}h {int(minutes)}m"
            else:
                ticket.wait_time_display = f"{int(minutes)}m"
        else:
            ticket.wait_time_display = "N/A"
    
    # Get currently serving
    currently_serving = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status == 'in_progress'
    ).first()
    
    # Get next citizen (prefer waiting over in_progress)
    waiting_tickets = [t for t in assigned_tickets if t.status == 'waiting']
    in_progress_tickets = [t for t in assigned_tickets if t.status == 'in_progress']
    
    next_citizen = None
    if waiting_tickets:
        next_citizen = waiting_tickets[0]
    elif in_progress_tickets:
        next_citizen = in_progress_tickets[0]
    
    # Basic metrics
    today = datetime.utcnow().date()
    citizens_served_today = Queue.query.filter(
        Queue.agent_id == agent.id,
        Queue.status == 'completed',
        func.date(Queue.updated_at) == today
    ).count()
    
    metrics = {
        'citizens_served_today': citizens_served_today,
        'avg_service_time': 15
    }
    
    # General queue for overview
    queue_items = Queue.query.filter(
        Queue.status.in_(['waiting', 'in_progress'])
    ).join(Citizen).join(ServiceType).order_by(
        desc(Queue.priority_score), Queue.created_at
    ).limit(10).all()
    
    return render_template('agent_dashboard.html',
                         agent=agent,
                         metrics=metrics,
                         currently_serving=currently_serving,
                         assigned_tickets=assigned_tickets,
                         next_citizen=next_citizen,
                         queue_items=queue_items,
                         datetime=datetime)

@agent_bp.route('/api/queue/next', methods=['GET'])
@login_required
def call_next_citizen():
    """Call next citizen in agent's queue"""
    try:
        agent = current_user
        
        # Get next assigned ticket for this agent
        next_ticket = Queue.query.filter(
            Queue.agent_id == agent.id,
            Queue.status == 'waiting'
        ).order_by(
            desc(Queue.priority_score), 
            Queue.created_at
        ).first()
        
        if not next_ticket:
            return jsonify({
                'success': False,
                'message': 'No tickets assigned to you'
            }), 400
        
        # Update ticket status
        next_ticket.status = 'in_progress'
        next_ticket.called_at = datetime.utcnow()
        next_ticket.updated_at = datetime.utcnow()
        
        # Update agent status
        agent.status = 'busy'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Called citizen: {next_ticket.citizen.first_name} {next_ticket.citizen.last_name}',
            'ticket_number': next_ticket.ticket_number,
            'citizen_name': f"{next_ticket.citizen.first_name} {next_ticket.citizen.last_name}",
            'service_name': next_ticket.service_type.name_fr if next_ticket.service_type else "Unknown Service"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error calling next citizen: {str(e)}'
        }), 500

@agent_bp.route('/profile')
@login_required
def agent_profile():
    """Agent profile page"""
    agent = current_user
    return render_template('agent_profile.html', agent=agent)

@agent_bp.route('/profile/update', methods=['POST'])
@login_required
def update_agent_profile():
    """Update agent profile"""
    try:
        data = request.get_json()
        
        # Get current agent
        agent = current_user
        
        # Update basic info
        if 'first_name' in data:
            agent.first_name = data['first_name']
        if 'last_name' in data:
            agent.last_name = data['last_name']
        if 'email' in data:
            agent.email = data['email']
        if 'phone' in data:
            agent.phone = data['phone']
        
        # Update password if provided
        if 'password' in data and data['password']:
            agent.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }), 500

@agent_bp.route('/settings')
@login_required
def agent_settings():
    """Agent settings page"""
    agent = current_user
    
    # Get available stations for assignment
    stations = Station.query.filter_by(is_active=True).all()
    
    # Get available service types for specializations
    service_types = ServiceType.query.filter_by(is_active=True).all()
    
    return render_template('agent_settings.html', 
                         agent=agent, 
                         stations=stations,
                         service_types=service_types)

@agent_bp.route('/settings/update', methods=['POST'])
@login_required
def update_agent_settings():
    """Update agent settings"""
    try:
        data = request.get_json()
        
        # Get current agent
        agent = current_user
        
        # Update notification preferences
        if 'email_notifications' in data:
            # For now, we'll store this in a simple way
            # In a real system, you'd have a separate preferences table
            pass
        
        # Update specializations if provided
        if 'specializations' in data:
            agent.specializations = data['specializations']
        
        # Update preferred station if provided
        if 'preferred_station_id' in data:
            agent.current_station_id = data['preferred_station_id']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating settings: {str(e)}'
        }), 500