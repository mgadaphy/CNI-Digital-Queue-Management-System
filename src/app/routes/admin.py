from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from ..models import db, Agent, ServiceType, Station, Citizen, Queue
from ..queue_logic.simple_optimizer import simple_optimizer
from .. import socketio
from ..extensions import csrf
from ..utils.websocket_utils import emit_queue_update, emit_agent_status_update, emit_metrics_update, websocket_error_handler
from ..utils.optimized_queries import query_optimizer
from ..utils.realtime_sync import emit_queue_update_sync, emit_agent_status_sync, emit_ticket_assignment_sync, emit_optimization_sync, EventPriority
from functools import wraps
import traceback
import logging

# Configure error logging
logging.basicConfig(level=logging.INFO)
error_logger = logging.getLogger('admin_errors')

def handle_database_errors(f):
    """Decorator to handle database errors consistently"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except IntegrityError as e:
            db.session.rollback()
            error_logger.error(f"Database integrity error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Data integrity error. Please check your input and try again.',
                'error_code': 'INTEGRITY_ERROR'
            }), 400
        except SQLAlchemyError as e:
            db.session.rollback()
            error_logger.error(f"Database error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Database error occurred. Please try again later.',
                'error_code': 'DATABASE_ERROR'
            }), 500
        except Exception as e:
            db.session.rollback()
            error_logger.error(f"Unexpected error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred. Please try again.',
                'error_code': 'INTERNAL_ERROR',
                'details': str(e) if current_app.debug else None
            }), 500
    return decorated_function

def validate_request_data(required_fields=None, optional_fields=None):
    """Decorator to validate request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.json and required_fields:
                return jsonify({
                    'success': False,
                    'message': 'Invalid request: JSON data required',
                    'error_code': 'INVALID_REQUEST'
                }), 400
            
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in request.json or not request.json[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'message': f'Missing required fields: {", ".join(missing_fields)}',
                        'error_code': 'MISSING_FIELDS'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# WebSocket emission functions moved to utils/websocket_utils.py
# Using enhanced emit_queue_update with retry mechanisms

# Agent status update function moved to utils/websocket_utils.py
# Using enhanced emit_agent_status_update with retry mechanisms

# Metrics update function moved to utils/websocket_utils.py
# Using enhanced emit_metrics_update with retry mechanisms
# The detailed metrics calculation logic is preserved in the new utility

@admin_bp.route('/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard with optimized metrics and active tickets display"""
    
    # Use optimized dashboard data retrieval
    dashboard_data = query_optimizer.get_dashboard_data()
    
    # Basic metrics (keep existing queries for non-performance critical data)
    total_agents = Agent.query.count()
    service_types_count = ServiceType.query.count()
    stations_count = Station.query.count()
    citizens_count = Citizen.query.count()
    
    # Extract optimized data
    stats = dashboard_data.get('statistics', {})
    queue_stats = stats.get('queue', {})
    agent_stats = stats.get('agents', {})
    active_tickets = dashboard_data.get('recent_tickets', [])
    
    # Calculate wait times for display (tickets already have related objects loaded)
    for ticket in active_tickets:
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
    
    # Get agent performance data with optimized queries
    agents = Agent.query.all()
    for agent in agents:
        # Use optimized performance metrics
        performance = query_optimizer.queue_queries.get_agent_performance_metrics(agent.id, days=1)
        agent.served_today = performance.get('served_today', 0)
    
    return render_template('admin_dashboard.html',
                         total_agents=total_agents,
                         active_agents=agent_stats.get('available', 0) + agent_stats.get('busy', 0),
                         service_types_count=service_types_count,
                         stations_count=stations_count,
                         citizens_count=citizens_count,
                         queue_waiting=queue_stats.get('waiting', 0),
                         queue_in_progress=queue_stats.get('in_progress', 0),
                         active_tickets=active_tickets,
                         agents=agents,
                         title='Admin Dashboard - CNI Digital Queue')

@admin_bp.route('/manage_agents')
@login_required
def manage_agents():
    """Manage agents page"""
    agents = Agent.query.all()
    return render_template('admin_agents.html', agents=agents)

@admin_bp.route('/create_agent')
@login_required
def create_agent():
    """Create new agent form"""
    return render_template('admin_create_agent.html')

@admin_bp.route('/edit_agent/<int:agent_id>')
@login_required
def edit_agent(agent_id):
    """Edit agent form"""
    agent = Agent.query.get_or_404(agent_id)
    return render_template('admin_edit_agent.html', agent=agent)

@admin_bp.route('/manage_service_types')
@login_required
def manage_service_types():
    """Manage service types page"""
    service_types = ServiceType.query.all()
    return render_template('admin_service_types.html', service_types=service_types)

@admin_bp.route('/create_service_type')
@login_required
def create_service_type():
    """Create new service type form"""
    return render_template('admin_create_service_type.html')

@admin_bp.route('/manage_stations')
@login_required
def manage_stations():
    """Manage stations page"""
    stations = Station.query.all()
    return render_template('admin_stations.html', stations=stations)

@admin_bp.route('/create_station')
@login_required
def create_station():
    """Create new station form"""
    return render_template('admin_create_station.html')

@admin_bp.route('/edit_station/<int:station_id>')
@login_required
def edit_station(station_id):
    """Edit station form"""
    station = Station.query.get_or_404(station_id)
    return render_template('admin_edit_station.html', station=station)

@admin_bp.route('/manage_citizens')
@login_required
def manage_citizens():
    """Manage citizens page"""
    citizens = Citizen.query.all()
    return render_template('admin_citizens.html', citizens=citizens)

@admin_bp.route('/manage_queue')
@login_required
def manage_queue():
    """Queue management page with pagination support"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)  # Default 50 items per page
    status_filter = request.args.get('status', '')
    
    # Build query with optional status filter
    query = Queue.query.join(Citizen).join(ServiceType).outerjoin(Agent)
    
    if status_filter:
        query = query.filter(Queue.status == status_filter)
    # Remove default filter to show all tickets by default
    # This allows users to see all 35 tickets instead of just waiting/in_progress ones
    
    # Apply pagination with optimized ordering
    queue_entries_paginated = query.order_by(
        desc(Queue.priority_score), Queue.created_at
    ).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # Get summary statistics for all statuses (cached for performance)
    queue_stats = {
        'waiting': Queue.query.filter_by(status='waiting').count(),
        'in_progress': Queue.query.filter_by(status='in_progress').count(),
        'completed_today': Queue.query.filter(
            Queue.status == 'completed',
            func.date(Queue.updated_at) == datetime.utcnow().date()
        ).count(),
        'total': Queue.query.count()
    }
    
    return render_template('admin_queue.html', 
                         queue_entries=queue_entries_paginated.items,
                         pagination=queue_entries_paginated,
                         queue_stats=queue_stats,
                         current_status_filter=status_filter)

@admin_bp.route('/system_reports')
@login_required
def system_reports():
    """System reports and analytics"""
    return render_template('admin_reports.html')

@admin_bp.route('/profile')
@login_required
def admin_profile():
    """Admin profile page"""
    return render_template('admin_profile.html')

@admin_bp.route('/settings')
@login_required
def admin_settings():
    """Admin settings page"""
    return render_template('admin_settings.html')

@admin_bp.route('/api/metrics/dashboard')
@login_required
@handle_database_errors
def get_dashboard_metrics():
    """API endpoint for real-time dashboard metrics"""
    try:
        from datetime import datetime, timedelta
        
        # Current timestamp
        now = datetime.utcnow()
        today = now.date()
        hour_ago = now - timedelta(hours=1)
        
        # Basic queue metrics
        queue_waiting = Queue.query.filter_by(status='waiting').count()
        queue_in_progress = Queue.query.filter_by(status='in_progress').count()
        queue_completed_today = Queue.query.filter(
            Queue.status == 'completed',
            func.date(Queue.updated_at) == today
        ).count()
        
        # Agent metrics
        total_agents = Agent.query.count()
        active_agents = Agent.query.filter_by(status='active').count()
        
        # Calculate average wait time for current queue
        waiting_tickets = Queue.query.filter_by(status='waiting').all()
        total_wait_time = 0
        wait_count = 0
        
        for ticket in waiting_tickets:
            if ticket.created_at:
                wait_time = (now - ticket.created_at).total_seconds() / 60  # minutes
                total_wait_time += wait_time
                wait_count += 1
        
        avg_wait_time = round(total_wait_time / wait_count, 1) if wait_count > 0 else 0
        
        # Calculate agent utilization
        agent_utilization = round((active_agents / total_agents * 100), 1) if total_agents > 0 else 0
        
        # Service time calculation (completed tickets in last hour)
        recent_completed = Queue.query.filter(
            Queue.status == 'completed',
            Queue.updated_at >= hour_ago
        ).all()
        
        total_service_time = 0
        service_count = 0
        
        for ticket in recent_completed:
            if ticket.created_at and ticket.updated_at:
                service_time = (ticket.updated_at - ticket.created_at).total_seconds() / 60
                total_service_time += service_time
                service_count += 1
        
        avg_service_time = round(total_service_time / service_count, 1) if service_count > 0 else 0
        
        # Peak hours analysis
        hourly_stats = []
        for i in range(24):
            hour_start = now.replace(hour=i, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)
            
            tickets_in_hour = Queue.query.filter(
                Queue.created_at >= hour_start,
                Queue.created_at < hour_end,
                func.date(Queue.created_at) == today
            ).count()
            
            hourly_stats.append({
                'hour': i,
                'tickets': tickets_in_hour
            })
        
        # Service type distribution
        service_distribution = db.session.query(
            ServiceType.name_en, # Or name_fr depending on desired language
            func.count(Queue.id).label('count')
        ).join(Queue).filter(
            func.date(Queue.created_at) == today
        ).group_by(ServiceType.name_en).all()
        
        service_dist_dict = {service.name_en: service.count for service in service_distribution}
        
        # Performance alerts
        alerts = []
        if avg_wait_time > 30:
            alerts.append({
                'type': 'warning',
                'message': f'High average wait time: {avg_wait_time} minutes',
                'timestamp': now.isoformat()
            })
        
        if queue_waiting > 20:
            alerts.append({
                'type': 'danger',
                'message': f'Queue backlog: {queue_waiting} tickets waiting',
                'timestamp': now.isoformat()
            })
        
        if agent_utilization < 50:
            alerts.append({
                'type': 'info',
                'message': f'Low agent utilization: {agent_utilization}%',
                'timestamp': now.isoformat()
            })
        
        return jsonify({
            'success': True,
            'data': {
                'current_metrics': {
                    'queue_waiting': queue_waiting,
                    'queue_in_progress': queue_in_progress,
                    'queue_completed_today': queue_completed_today,
                    'total_agents': total_agents,
                    'active_agents': active_agents,
                    'average_wait_time': avg_wait_time,
                    'agent_utilization': agent_utilization,
                    'average_service_time': avg_service_time
                },
                'hourly_distribution': hourly_stats,
                'service_distribution': service_dist_dict,
                'alerts': alerts,
                'last_updated': now.isoformat()
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/refresh_tickets')
@login_required
@handle_database_errors
def refresh_tickets():
    """API endpoint to refresh active tickets data with optimized pagination"""
    # Check if request is AJAX and user is not authenticated
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'tickets': []}), 401
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        status_filter = request.args.get('status', '')
        
        # Use optimized query method
        result = query_optimizer.refresh_tickets_optimized(
            page=page,
            per_page=per_page,
            status_filter=status_filter if status_filter else None
        )
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_details = {
            'success': False,
            'error': str(e),
            'type': type(e).__name__,
            'traceback': traceback.format_exc(),
            'tickets': [],
            'count': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        error_logger.error(f"Error in refresh_tickets: {error_details}")
        return jsonify(error_details), 500

@admin_bp.route('/api/assign_ticket/<int:ticket_id>', methods=['POST'])
@login_required
@handle_database_errors
def assign_ticket(ticket_id):
    """API endpoint to assign a ticket to an agent with comprehensive validation"""
    # Check if request is AJAX and user is not authenticated
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        # Get agent_id from request if provided, otherwise auto-assign
        agent_id = None
        if request.json:
            agent_id = request.json.get('agent_id')
        
        # If no agent_id provided, auto-assign to available agent with load balancing
        if not agent_id:
            current_app.logger.info(f"Auto-assigning ticket {ticket_id} - looking for available agents")
            
            # Get all available agents
            available_agents = Agent.query.filter_by(
                status='available',
                is_active=True
            ).all()
            
            if not available_agents:
                current_app.logger.warning(f"No available agents found for ticket {ticket_id}")
                # Check what agents exist and their statuses
                all_agents = Agent.query.filter_by(is_active=True).all()
                agent_statuses = [f"{a.first_name} {a.last_name}: {a.status}" for a in all_agents]
                current_app.logger.info(f"All agents: {agent_statuses}")
                
                return jsonify({
                    'success': False, 
                    'message': 'No available agents found for assignment',
                    'error_code': 'NO_AVAILABLE_AGENTS'
                }), 400
            
            # Load balance: find agent with fewest active tickets
            best_agent = None
            min_tickets = float('inf')
            
            for agent in available_agents:
                current_tickets = Queue.query.filter(
                    Queue.agent_id == agent.id,
                    Queue.status.in_(['waiting', 'in_progress'])
                ).count()
                
                current_app.logger.info(f"Agent {agent.first_name} {agent.last_name} has {current_tickets} tickets")
                
                if current_tickets < min_tickets:
                    min_tickets = current_tickets
                    best_agent = agent
            
            if not best_agent:
                return jsonify({
                    'success': False, 
                    'message': 'No suitable agent found for assignment',
                    'error_code': 'NO_SUITABLE_AGENT'
                }), 400
            
            agent_id = best_agent.id
            current_app.logger.info(f"Load-balanced assignment: ticket {ticket_id} to agent {agent_id} ({best_agent.first_name} {best_agent.last_name}) with {min_tickets} existing tickets")
        
        # Validate ticket exists and is assignable
        ticket = Queue.query.get(ticket_id)
        if not ticket:
            return jsonify({
                'success': False, 
                'message': f'Ticket with ID {ticket_id} not found',
                'error_code': 'TICKET_NOT_FOUND'
            }), 404
        
        if ticket.status not in ['waiting', 'in_progress']:
            return jsonify({
                'success': False, 
                'message': f'Ticket cannot be assigned. Current status: {ticket.status}',
                'error_code': 'INVALID_TICKET_STATUS'
            }), 400
        
        # Validate agent exists and is available
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({
                'success': False, 
                'message': f'Agent with ID {agent_id} not found',
                'error_code': 'AGENT_NOT_FOUND'
            }), 404
        
        if agent.status not in ['available', 'busy']:
            return jsonify({
                'success': False, 
                'message': f'Agent {agent.first_name} {agent.last_name} is not available (Status: {agent.status})',
                'error_code': 'AGENT_UNAVAILABLE'
            }), 400
        
        # Check if agent is already handling maximum tickets
        current_tickets = Queue.query.filter_by(
            agent_id=agent_id, 
            status='in_progress'
        ).count()
        
        max_concurrent = getattr(agent, 'max_concurrent_tickets', 3)  # Default limit
        if current_tickets >= max_concurrent:
            return jsonify({
                'success': False, 
                'message': f'Agent {agent.first_name} {agent.last_name} is at maximum capacity ({current_tickets}/{max_concurrent} tickets)',
                'error_code': 'AGENT_AT_CAPACITY'
            }), 400
        
        # Store previous state for rollback
        previous_agent_id = ticket.agent_id
        previous_status = ticket.status
        
        # Update ticket assignment
        ticket.agent_id = agent_id
        ticket.status = 'in_progress'
        ticket.updated_at = datetime.utcnow()
        
        # Commit changes
        db.session.commit()
        
        # Emit synchronized real-time updates
        emit_ticket_assignment_sync(
            ticket_id=ticket.id,
            agent_id=agent_id,
            previous_status=previous_status
        )
        
        emit_agent_status_sync(
            agent_id=agent_id,
            status='busy',
            metrics={
                'current_tickets': current_tickets + 1,
                'max_capacity': max_concurrent,
                'assigned_ticket': ticket.id
            }
        )
        
        current_app.logger.info(
            f"Ticket {ticket_id} assigned to agent {agent_id} ({agent.first_name} {agent.last_name}) by user {current_user.id}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Ticket #{ticket.id} successfully assigned to {agent.first_name} {agent.last_name}',
            'data': {
                'ticket_id': ticket.id,
                'agent_id': agent_id,
                'agent_name': f'{agent.first_name} {agent.last_name}',
                'status': ticket.status,
                'assigned_at': ticket.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error assigning ticket {ticket_id}: {str(e)}", 
            exc_info=True
        )
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred while assigning the ticket',
            'error_code': 'INTERNAL_ERROR',
            'details': str(e) if current_app.debug else None
        }), 500

@admin_bp.route('/api/ticket_details/<int:ticket_id>')
@login_required
def ticket_details(ticket_id):
    """API endpoint to get detailed ticket information"""
    # Check if request is AJAX and user is not authenticated
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    ticket = Queue.query.get(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    
    return jsonify({
        'id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'citizen': {
            'name': f"{ticket.citizen.first_name} {ticket.citizen.last_name}",
            'enrollment_code': ticket.citizen.pre_enrollment_code
        },
        'service_type': ticket.service_type.name_fr,
        'priority_score': ticket.priority_score,
        'status': ticket.status,
        'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
        'assigned_agent': {
            'name': f"{ticket.agent.first_name} {ticket.agent.last_name}",
            'id': ticket.agent.id
        } if ticket.agent else None
    })

@admin_bp.route('/api/complete_ticket/<int:ticket_id>', methods=['POST'])
@login_required
@handle_database_errors
def complete_ticket(ticket_id):
    """API endpoint to mark a ticket as completed with comprehensive validation"""
    try:
        # Validate ticket exists
        ticket = Queue.query.get(ticket_id)
        if not ticket:
            return jsonify({
                'success': False,
                'message': f'Ticket with ID {ticket_id} not found',
                'error_code': 'TICKET_NOT_FOUND'
            }), 404
        
        # Validate ticket can be completed
        if ticket.status == 'completed':
            return jsonify({
                'success': False,
                'message': f'Ticket #{ticket.id} is already completed',
                'error_code': 'ALREADY_COMPLETED'
            }), 400
        
        if ticket.status not in ['in_progress', 'waiting']:
            return jsonify({
                'success': False,
                'message': f'Ticket cannot be completed. Current status: {ticket.status}',
                'error_code': 'INVALID_STATUS_TRANSITION'
            }), 400
        
        # Validate user permissions (agents can only complete their own tickets)
        if hasattr(current_user, 'agent') and current_user.agent:
            if ticket.agent_id != current_user.agent.id:
                return jsonify({
                    'success': False,
                    'message': 'You can only complete tickets assigned to you',
                    'error_code': 'UNAUTHORIZED_COMPLETION'
                }), 403
        
        # Get completion notes if provided
        completion_notes = None
        if request.json:
            completion_notes = request.json.get('notes', '').strip()
        
        # Store previous state for logging
        previous_status = ticket.status
        previous_agent_id = ticket.agent_id
        
        # Update ticket status
        ticket.status = 'completed'
        ticket.completed_at = datetime.utcnow()
        ticket.updated_at = datetime.utcnow()
        
        # Add completion notes if provided
        if completion_notes:
            ticket.notes = (ticket.notes or '') + f'\n[Completed] {completion_notes}'
        
        # Calculate service time
        service_time = None
        if ticket.started_at:
            service_time = (ticket.completed_at - ticket.started_at).total_seconds() / 60  # in minutes
            ticket.service_time = service_time
        
        # Commit changes
        db.session.commit()
        
        # Update agent availability if they were assigned
        if previous_agent_id:
            agent = Agent.query.get(previous_agent_id)
            if agent:
                # Check remaining tickets for this agent
                remaining_tickets = Queue.query.filter_by(
                    agent_id=previous_agent_id,
                    status='in_progress'
                ).count()
                
                # Update agent status if no more tickets
                if remaining_tickets == 0:
                    emit_agent_status_update(previous_agent_id, 'available', {
                        'current_tickets': 0,
                        'last_completed': ticket.completed_at.isoformat()
                    })
        
        # Emit real-time updates
        emit_queue_update(
            f'Ticket #{ticket.id} completed',
            'completion',
            {
                'ticket_id': ticket.id,
                'previous_status': previous_status,
                'service_time': service_time,
                'completed_by': current_user.username
            }
        )
        
        # Trigger metrics update
        emit_metrics_update()
        
        current_app.logger.info(
            f"Ticket {ticket_id} completed by user {current_user.id}. Service time: {service_time:.1f} minutes" if service_time else f"Ticket {ticket_id} completed by user {current_user.id}"
        )
        
        return jsonify({
            'success': True,
            'message': f'Ticket #{ticket.id} successfully completed',
            'data': {
                'ticket_id': ticket.id,
                'completed_at': ticket.completed_at.isoformat(),
                'service_time': f"{service_time:.1f} minutes" if service_time else None,
                'previous_status': previous_status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"Error completing ticket {ticket_id}: {str(e)}",
            exc_info=True
        )
        return jsonify({
            'success': False,
            'message': 'An unexpected error occurred while completing the ticket',
            'error_code': 'INTERNAL_ERROR',
            'details': str(e) if current_app.debug else None
        }), 500

@admin_bp.route('/api/queue/optimize', methods=['POST'])
# @login_required  # Temporarily disabled for testing
@handle_database_errors
@csrf.exempt  # Temporarily disabled for testing
def optimize_queue():
    """API endpoint to optimize queue order"""
    # Check if request is AJAX and user is not authenticated
    # if not current_user.is_authenticated:  # Temporarily disabled for testing
    #     return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        # Use simplified optimizer
        result = simple_optimizer.optimize_queue()
        
        if result.success:
            # Get affected tickets for synchronization
            affected_tickets = Queue.query.filter_by(status='waiting').with_entities(Queue.id).all()
            affected_ticket_ids = [ticket.id for ticket in affected_tickets]
            
            # Emit synchronized WebSocket update
            emit_optimization_sync(
                optimized_count=result.optimized_count,
                total_tickets=result.total_tickets,
                affected_tickets=affected_ticket_ids
            )
            
            current_app.logger.info(f"Simple queue optimization completed: {result.optimized_count}/{result.total_tickets} tickets optimized")
            
            return jsonify({
                'success': True,
                'message': result.message,
                'optimized_count': result.optimized_count,
                'total_tickets': result.total_tickets
            })
        else:
            return jsonify({
                'success': False,
                'message': result.message
            }), 400
            
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error in queue optimization: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Queue optimization failed: {str(e)}'
        }), 500


@admin_bp.route('/queue/<int:queue_id>/call-next', methods=['POST'])
@login_required
@handle_database_errors
def call_next_ticket(queue_id):
    """API endpoint to call next ticket in queue"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        ticket = Queue.query.get_or_404(queue_id)
        
        if ticket.status != 'waiting':
            return jsonify({
                'success': False,
                'message': 'Ticket is not in waiting status'
            }), 400
        
        # Update ticket status to in_progress
        ticket.status = 'in_progress'
        ticket.updated_at = datetime.utcnow()
        
        # If ticket has an assigned agent, update agent status
        if ticket.agent:
            ticket.agent.status = 'busy'
        
        db.session.commit()
        
        # Emit WebSocket update
        emit_queue_update()
        
        return jsonify({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} is now being served',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'status': ticket.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error calling next ticket {queue_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/queue/<int:queue_id>/update-priority', methods=['POST'])
@login_required
@handle_database_errors
@validate_request_data(required_fields=['priority'])
def update_ticket_priority(queue_id):
    """API endpoint to update ticket priority"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        ticket = Queue.query.get_or_404(queue_id)
        data = request.get_json()
        new_priority = data.get('priority')
        
        # Validate priority value
        try:
            new_priority = float(new_priority)
            if new_priority < 0 or new_priority > 100:
                return jsonify({
                    'success': False,
                    'message': 'Priority must be between 0 and 100'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Invalid priority value'
            }), 400
        
        # Update ticket priority
        old_priority = ticket.priority_score
        ticket.priority_score = new_priority
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Emit WebSocket update
        emit_queue_update()
        
        return jsonify({
            'success': True,
            'message': f'Priority updated from {old_priority} to {new_priority}',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'priority_score': ticket.priority_score
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error updating priority for ticket {queue_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/queue/<int:queue_id>/cancel', methods=['POST'])
@login_required
@handle_database_errors
def cancel_ticket(queue_id):
    """API endpoint to cancel a ticket"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        ticket = Queue.query.get_or_404(queue_id)
        
        if ticket.status == 'completed':
            return jsonify({
                'success': False,
                'message': 'Cannot cancel a completed ticket'
            }), 400
        
        # Update ticket status to cancelled
        old_status = ticket.status
        ticket.status = 'cancelled'
        ticket.updated_at = datetime.utcnow()
        
        # If ticket was assigned to an agent, free up the agent
        if ticket.agent and old_status == 'in_progress':
            ticket.agent.status = 'available'
        
        db.session.commit()
        
        # Emit WebSocket update
        emit_queue_update()
        
        return jsonify({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} has been cancelled',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'status': ticket.status
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error cancelling ticket {queue_id}: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/api/queue/<int:queue_id>/details')
@login_required
def queue_ticket_details(queue_id):
    """API endpoint to get detailed queue ticket information"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required'}), 401
    
    ticket = Queue.query.get_or_404(queue_id)
    
    return jsonify({
        'id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'citizen': {
            'name': f"{ticket.citizen.first_name} {ticket.citizen.last_name}",
            'enrollment_code': ticket.citizen.pre_enrollment_code
        },
        'service_type': ticket.service_type.name_fr,
        'priority_score': ticket.priority_score,
        'status': ticket.status,
        'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
        'assigned_agent': {
            'name': f"{ticket.agent.first_name} {ticket.agent.last_name}",
            'id': ticket.agent.id
        } if ticket.agent else None
    })

@admin_bp.route('/api/queue/<int:queue_id>/call-next', methods=['POST'])
@login_required
@handle_database_errors
def call_next_ticket_api(queue_id):
    """API endpoint to call next ticket in queue - Enhanced version"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        ticket = Queue.query.get_or_404(queue_id)
        
        if ticket.status != 'waiting':
            return jsonify({
                'success': False,
                'message': f'Ticket cannot be called. Current status: {ticket.status}'
            }), 400
        
        # Update ticket status to in_progress
        ticket.status = 'in_progress'
        ticket.updated_at = datetime.utcnow()
        
        # If ticket has an assigned agent, update agent status
        if ticket.agent:
            ticket.agent.status = 'busy'
        
        db.session.commit()
        
        # Emit WebSocket update
        emit_queue_update(
            f'Ticket #{ticket.ticket_number} is now being served',
            'call_next',
            {
                'ticket_id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'status': ticket.status,
                'agent_id': ticket.agent.id if ticket.agent else None
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} is now being served',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'status': ticket.status,
                'citizen_name': f"{ticket.citizen.first_name} {ticket.citizen.last_name}" if ticket.citizen else "Unknown",
                'service_name': ticket.service_type.name_fr if ticket.service_type else "Unknown Service"
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error calling next ticket {queue_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error calling ticket: {str(e)}'
        }), 500

@admin_bp.route('/api/queue/<int:queue_id>/update-priority', methods=['PUT'])
@login_required
@handle_database_errors
def update_ticket_priority_api(queue_id):
    """API endpoint to update ticket priority - Enhanced version"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        ticket = Queue.query.get_or_404(queue_id)
        
        if not request.json:
            return jsonify({
                'success': False,
                'message': 'Invalid request: JSON data required'
            }), 400
        
        new_priority = request.json.get('priority')
        
        # Validate priority value
        try:
            new_priority = float(new_priority)
            if new_priority < 0 or new_priority > 100:
                return jsonify({
                    'success': False,
                    'message': 'Priority must be between 0 and 100'
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'message': 'Invalid priority value'
            }), 400
        
        # Update ticket priority
        old_priority = ticket.priority_score
        ticket.priority_score = new_priority
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Emit WebSocket update
        emit_queue_update(
            f'Priority updated for ticket #{ticket.ticket_number}',
            'priority_update',
            {
                'ticket_id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'old_priority': old_priority,
                'new_priority': new_priority
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Priority updated from {old_priority} to {new_priority}',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'priority_score': ticket.priority_score,
                'old_priority': old_priority
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error updating priority for ticket {queue_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error updating priority: {str(e)}'
        }), 500

@admin_bp.route('/api/queue/<int:queue_id>/cancel', methods=['POST'])
@login_required
@handle_database_errors
def cancel_ticket_api(queue_id):
    """API endpoint to cancel a ticket - Enhanced version"""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        ticket = Queue.query.get_or_404(queue_id)
        
        if ticket.status == 'completed':
            return jsonify({
                'success': False,
                'message': 'Cannot cancel a completed ticket'
            }), 400
        
        if ticket.status == 'cancelled':
            return jsonify({
                'success': False,
                'message': 'Ticket is already cancelled'
            }), 400
        
        # Get cancellation reason if provided
        cancellation_reason = None
        if request.json:
            cancellation_reason = request.json.get('reason', '').strip()
        
        # Update ticket status to cancelled
        old_status = ticket.status
        ticket.status = 'cancelled'
        ticket.updated_at = datetime.utcnow()
        
        # Add cancellation reason to notes
        if cancellation_reason:
            ticket.notes = (ticket.notes or '') + f'\n[Cancelled] {cancellation_reason}'
        
        # If ticket was assigned to an agent, free up the agent
        if ticket.agent and old_status == 'in_progress':
            # Check if agent has other active tickets
            remaining_tickets = Queue.query.filter_by(
                agent_id=ticket.agent.id,
                status='in_progress'
            ).filter(Queue.id != ticket.id).count()
            
            if remaining_tickets == 0:
                ticket.agent.status = 'available'
        
        db.session.commit()
        
        # Emit WebSocket update
        emit_queue_update(
            f'Ticket #{ticket.ticket_number} has been cancelled',
            'cancellation',
            {
                'ticket_id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'previous_status': old_status,
                'reason': cancellation_reason
            }
        )
        
        return jsonify({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} has been cancelled',
            'ticket': {
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'status': ticket.status,
                'previous_status': old_status,
                'cancellation_reason': cancellation_reason
            }
        })
        
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error cancelling ticket {queue_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error cancelling ticket: {str(e)}'
        }), 500

@admin_bp.route('/api/queue/optimize', methods=['POST'])
# @login_required  # Temporarily disabled for testing
@handle_database_errors
def optimize_queue_api():
    """API endpoint to optimize the queue - Enhanced version"""
    # if not current_user.is_authenticated:  # Temporarily disabled for testing
    #     return jsonify({'error': 'Authentication required', 'success': False}), 401
    
    try:
        # Use simplified optimizer (same as first endpoint)
        result = simple_optimizer.optimize_queue()
        
        if result.success:
            # Get affected tickets for synchronization
            affected_tickets = Queue.query.filter_by(status='waiting').with_entities(Queue.id).all()
            affected_ticket_ids = [ticket.id for ticket in affected_tickets]
            
            # Emit synchronized WebSocket update
            emit_optimization_sync(
                optimized_count=result.optimized_count,
                total_tickets=result.total_tickets,
                affected_tickets=affected_ticket_ids
            )
            
            return jsonify({
                'success': True,
                'message': result.message,
                'optimized_count': result.optimized_count,
                'total_tickets': result.total_tickets
            })
        else:
            return jsonify({
                'success': False,
                'message': result.message
            }), 400
            
    except Exception as e:
        db.session.rollback()
        error_logger.error(f"Error optimizing queue: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Error optimizing queue: {str(e)}'
        }), 500

# Missing Service Type Management Routes
@admin_bp.route('/edit_service_type/<int:service_type_id>')
@login_required
def edit_service_type(service_type_id):
    """Edit service type form"""
    service_type = ServiceType.query.get_or_404(service_type_id)
    return render_template('admin_edit_service_type.html', service_type=service_type)

@admin_bp.route('/api/service_type/<int:service_type_id>', methods=['PUT'])
@login_required
def update_service_type(service_type_id):
    """Update service type"""
    try:
        service_type = ServiceType.query.get_or_404(service_type_id)
        data = request.get_json()
        
        service_type.name_fr = data.get('name_fr', service_type.name_fr)
        service_type.name_en = data.get('name_en', service_type.name_en)
        service_type.description_fr = data.get('description_fr', service_type.description_fr)
        service_type.description_en = data.get('description_en', service_type.description_en)
        service_type.priority_level = data.get('priority_level', service_type.priority_level)
        service_type.estimated_duration = data.get('estimated_duration', service_type.estimated_duration)
        service_type.is_active = data.get('is_active', service_type.is_active)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service type updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating service type: {str(e)}'
        }), 500

# Missing Station Management Routes
@admin_bp.route('/api/station/<int:station_id>/status', methods=['PUT'])
@login_required
def update_station_status(station_id):
    """Update station status"""
    try:
        station = Station.query.get_or_404(station_id)
        data = request.get_json()
        
        new_status = data.get('status')
        if new_status not in ['available', 'maintenance', 'offline']:
            return jsonify({
                'success': False,
                'message': 'Invalid status. Must be: available, maintenance, or offline'
            }), 400
        
        station.status = new_status
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Station status updated to {new_status}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating station status: {str(e)}'
        }), 500

@admin_bp.route('/api/station/<int:station_id>', methods=['PUT'])
@login_required
def update_station(station_id):
    """Update station details"""
    try:
        station = Station.query.get_or_404(station_id)
        data = request.get_json()
        
        station.name = data.get('name', station.name)
        station.description = data.get('description', station.description)
        station.location = data.get('location', station.location)
        station.supported_services = data.get('supported_services', station.supported_services)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Station updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error updating station: {str(e)}'
        }), 500

# Missing Service Type Delete Route
@admin_bp.route('/api/service_type/<int:service_type_id>', methods=['DELETE'])
@login_required
def delete_service_type(service_type_id):
    """Delete service type"""
    try:
        service_type = ServiceType.query.get_or_404(service_type_id)
        
        # Check if service type is in use
        active_tickets = Queue.query.filter_by(service_type_id=service_type_id).count()
        if active_tickets > 0:
            return jsonify({
                'success': False,
                'message': f'Cannot delete service type. {active_tickets} tickets are using this service type.'
            }), 400
        
        db.session.delete(service_type)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Service type deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting service type: {str(e)}'
        }), 500

# Missing Station Toggle Route
@admin_bp.route('/api/station/<int:station_id>/toggle', methods=['POST'])
@login_required
def toggle_station(station_id):
    """Toggle station status between available and offline"""
    try:
        station = Station.query.get_or_404(station_id)
        
        # Toggle between available and offline
        if station.status == 'available':
            station.status = 'offline'
            message = 'Station set to offline'
        else:
            station.status = 'available'
            message = 'Station set to available'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message,
            'new_status': station.status
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error toggling station status: {str(e)}'
        }), 500

# Missing Citizen Management Routes
@admin_bp.route('/citizens/<int:citizen_id>/view')
@login_required
def view_citizen(citizen_id):
    """View citizen details"""
    citizen = Citizen.query.get_or_404(citizen_id)
    return render_template('admin_citizen_view.html', citizen=citizen)

@admin_bp.route('/citizens/<int:citizen_id>/edit')
@login_required
def edit_citizen(citizen_id):
    """Edit citizen form"""
    citizen = Citizen.query.get_or_404(citizen_id)
    return render_template('admin_edit_citizen.html', citizen=citizen)

@admin_bp.route('/citizens/<int:citizen_id>/history')
@login_required
def citizen_history(citizen_id):
    """Get citizen ticket history"""
    try:
        citizen = Citizen.query.get_or_404(citizen_id)
        
        # Get ticket history
        tickets = Queue.query.filter_by(citizen_id=citizen_id).order_by(desc(Queue.created_at)).all()
        
        history_data = []
        for ticket in tickets:
            history_data.append({
                'ticket_number': ticket.ticket_number,
                'service_type': ticket.service_type.name_fr if ticket.service_type else 'Unknown',
                'status': ticket.status,
                'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M'),
                'completed_at': ticket.completed_at.strftime('%Y-%m-%d %H:%M') if ticket.completed_at else None,
                'agent_name': f"{ticket.agent.first_name} {ticket.agent.last_name}" if ticket.agent else 'Unassigned'
            })
        
        return jsonify({
            'success': True,
            'citizen': {
                'name': f"{citizen.first_name} {citizen.last_name}",
                'pe_code': citizen.pre_enrollment_code
            },
            'history': history_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting citizen history: {str(e)}'
        }), 500

@admin_bp.route('/citizens/<int:citizen_id>/deactivate', methods=['POST'])
@login_required
def deactivate_citizen(citizen_id):
    """Deactivate citizen"""
    try:
        citizen = Citizen.query.get_or_404(citizen_id)
        citizen.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Citizen deactivated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deactivating citizen: {str(e)}'
        }), 500

@admin_bp.route('/citizens/<int:citizen_id>/activate', methods=['POST'])
@login_required
def activate_citizen(citizen_id):
    """Activate citizen"""
    try:
        citizen = Citizen.query.get_or_404(citizen_id)
        citizen.is_active = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Citizen activated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error activating citizen: {str(e)}'
        }), 500

# Agent Details Route for Admin
@admin_bp.route('/api/agents/list')
@login_required
def list_agents():
    """Get list of all agents with their details"""
    try:
        agents = Agent.query.all()
        
        agents_data = []
        for agent in agents:
            # Get current ticket counts
            active_tickets = Queue.query.filter_by(
                agent_id=agent.id,
                status='in_progress'
            ).count()
            
            waiting_tickets = Queue.query.filter_by(
                agent_id=agent.id,
                status='waiting'
            ).count()
            
            agents_data.append({
                'id': agent.id,
                'name': f"{agent.first_name} {agent.last_name}",
                'employee_id': agent.employee_id,
                'email': agent.email,
                'status': agent.status,
                'is_active': agent.is_active,
                'role': agent.role,
                'current_station_id': agent.current_station_id,
                'active_tickets': active_tickets,
                'waiting_tickets': waiting_tickets,
                'login_time': agent.login_time.isoformat() if agent.login_time else None,
                'logout_time': agent.logout_time.isoformat() if agent.logout_time else None
            })
        
        return jsonify({
            'success': True,
            'agents': agents_data,
            'total': len(agents_data)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error getting agents list: {str(e)}'
        }), 500

@admin_bp.route('/api/unassign_ticket/<int:ticket_id>', methods=['POST'])
@login_required
def unassign_ticket(ticket_id):
    """Unassign a ticket from an agent"""
    try:
        ticket = Queue.query.get(ticket_id)
        if not ticket:
            return jsonify({
                'success': False,
                'message': f'Ticket with ID {ticket_id} not found'
            }), 404
        
        if not ticket.agent_id:
            return jsonify({
                'success': False,
                'message': 'Ticket is not assigned to any agent'
            }), 400
        
        # Store previous agent for logging
        previous_agent = ticket.agent
        previous_agent_name = f"{previous_agent.first_name} {previous_agent.last_name}" if previous_agent else "Unknown"
        
        # Unassign the ticket
        ticket.agent_id = None
        ticket.status = 'waiting'  # Reset to waiting status
        ticket.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        current_app.logger.info(f"Ticket {ticket_id} unassigned from agent {previous_agent_name}")
        
        return jsonify({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} unassigned from {previous_agent_name}',
            'ticket_id': ticket_id,
            'ticket_number': ticket.ticket_number
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error unassigning ticket {ticket_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error unassigning ticket: {str(e)}'
        }), 500