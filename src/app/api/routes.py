from flask import request, jsonify
from . import api_bp
from ..models import Agent, Citizen, Queue, ServiceType
from ..extensions import db, socketio
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..queue_logic.optimizer import calculate_priority_score, get_next_citizen_in_queue
from ..utils.websocket_utils import emit_queue_update, emit_agent_status_update, emit_metrics_update
from ..utils.db_transaction_manager import get_transaction_manager, optimized_transaction
from datetime import datetime, time
from sqlalchemy import func

@api_bp.route('/check-in', methods=['POST'])
@jwt_required()
@optimized_transaction(retry_on_failure=True)
def check_in(session):
    data = request.get_json()
    pre_enrollment_code = data.get('pre_enrollment_code')

    if not pre_enrollment_code:
        return jsonify({'message': 'Pre-enrollment code is required'}), 400

    # Placeholder for IDCAM integration
    # For now, we'll assume the code is valid and find/create a citizen record.
    citizen = session.query(Citizen).filter_by(pre_enrollment_code=pre_enrollment_code).first()
    if not citizen:
        # In a real scenario, we would fetch details from IDCAM
        # Here, we'll create a dummy citizen for demonstration
        citizen = Citizen(
            pre_enrollment_code=pre_enrollment_code,
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01'
        )
        session.add(citizen)
        session.flush()

    # For now, assign a default service type (e.g., ID 1)
    # In a real app, this might be selected by the citizen
    service_type_id = data.get('service_type_id', 1)
    service = session.query(ServiceType).get(service_type_id)
    if not service:
        return jsonify({'message': 'Service type not found'}), 404

    # Generate a simple ticket number
    ticket_number = f"T-{citizen.id}-{datetime.utcnow().strftime('%H%M%S')}"

    # Calculate priority score
    priority_score = calculate_priority_score(citizen, service)

    # Create a queue entry
    new_queue_entry = Queue(
        citizen_id=citizen.id,
        service_type_id=service_type_id,
        ticket_number=ticket_number,
        priority_score=priority_score
    )
    session.add(new_queue_entry)
    session.flush()
    
    # Emit enhanced queue update
    emit_queue_update(
        'A new citizen has checked in.',
        update_type='checkin',
        data={
            'citizen_id': citizen.id,
            'ticket_number': ticket_number,
            'priority_score': priority_score,
            'service_type': service.name
        }
    )

    return jsonify({
        'message': f'Citizen {citizen.pre_enrollment_code} checked in successfully',
        'ticket_number': ticket_number,
        'priority_score': priority_score
    }), 201

@api_bp.route('/queue/next', methods=['GET'])
@jwt_required()
@optimized_transaction(retry_on_failure=True)
def get_next(session):
    """Get the next citizen from the queue and assign to the current agent."""
    agent_id = int(get_jwt_identity())
    next_in_queue = session.query(Queue).filter_by(status='waiting').order_by(
        Queue.priority_score.desc(),
        Queue.created_at.asc()
    ).first()

    if not next_in_queue:
        return jsonify({'message': 'The queue is currently empty'}), 404

    # Update the queue entry and agent status
    next_in_queue.status = 'in_progress'
    next_in_queue.agent_id = agent_id
    next_in_queue.called_at = datetime.utcnow()

    agent = session.query(Agent).get(agent_id)
    agent.status = 'busy'

    session.flush()
    
    # Emit enhanced updates
    emit_queue_update(
        'A citizen has been called.',
        update_type='call_next',
        data={
            'citizen_id': next_in_queue.citizen_id,
            'ticket_number': next_in_queue.ticket_number,
            'agent_id': agent_id
        }
    )
    
    emit_agent_status_update(agent.id, agent.status)

    return jsonify({
        'message': 'Next citizen called',
        'ticket_number': next_in_queue.ticket_number,
        'citizen_id': next_in_queue.citizen_id,
        'service_type': next_in_queue.service_type.name_en
    }), 200


@api_bp.route('/agent/status', methods=['PUT'])
@jwt_required()
@optimized_transaction(retry_on_failure=True)
def update_agent_status(session):
    """Update the status of the currently authenticated agent."""
    agent_id = int(get_jwt_identity())
    data = request.get_json()
    new_status = data.get('status')

    if not new_status:
        return jsonify({'message': 'Status is required'}), 400

    valid_statuses = ['available', 'on_break', 'offline', 'busy']
    if new_status not in valid_statuses:
        return jsonify({'message': f'Invalid status. Must be one of {valid_statuses}'}), 400

    agent = session.query(Agent).get(agent_id)
    if not agent:
        return jsonify({'message': 'Agent not found'}), 404

    agent.status = new_status
    session.flush()

    emit_agent_status_update(agent.id, agent.status)

    return jsonify({'message': f'Agent status updated to {new_status}'}), 200

@api_bp.route('/queue/complete', methods=['POST'])
@jwt_required()
@optimized_transaction(retry_on_failure=True)
def complete_service(session):
    """Mark the current service as completed for the authenticated agent."""
    agent_id = int(get_jwt_identity())
    data = request.get_json()
    queue_id = data.get('queue_id')

    if not queue_id:
        return jsonify({'message': 'Queue ID is required'}), 400

    queue_entry = session.query(Queue).get(queue_id)
    if not queue_entry or queue_entry.agent_id != agent_id:
        return jsonify({'message': 'Queue entry not found or not assigned to this agent'}), 404

    queue_entry.status = 'completed'
    queue_entry.completed_at = datetime.utcnow()

    agent = session.query(Agent).get(agent_id)
    agent.status = 'available'

    session.flush()

    # Recalculate metrics for the agent
    today_start = datetime.combine(datetime.utcnow().date(), time.min)
    citizens_served_today = session.query(Queue).filter(
        Queue.agent_id == agent_id,
        Queue.status == 'completed',
        Queue.completed_at >= today_start
    ).count()

    avg_service_time_query = session.query(func.avg(Queue.completed_at - Queue.called_at)).filter(
        Queue.agent_id == agent_id,
        Queue.status == 'completed',
        Queue.completed_at.isnot(None),
        Queue.called_at.isnot(None)
    ).scalar()
    
    avg_service_time = avg_service_time_query.total_seconds() / 60 if avg_service_time_query else 0

    metrics = {
        'citizens_served_today': citizens_served_today,
        'avg_service_time': round(avg_service_time, 2)
    }

    # Emit enhanced updates
    emit_queue_update(
        'Service completed.',
        update_type='completion',
        data={
            'queue_id': queue_entry.id,
            'citizen_id': queue_entry.citizen_id,
            'agent_id': agent.id
        }
    )
    
    emit_agent_status_update(
        agent.id, 
        agent.status, 
        metrics=metrics
    )
    
    emit_metrics_update({
        'agent_id': agent.id, 
        'metrics': metrics,
        'update_type': 'service_completion'
    })

    return jsonify({'message': 'Service completed successfully', 'metrics': metrics}), 200

@api_bp.route('/queue', methods=['GET'])
@jwt_required()
@optimized_transaction(retry_on_failure=False)
def get_queue(session):
    """Get the current queue status with enhanced transaction handling"""
    try:
        # Get all waiting queue entries
        queue_entries = session.query(Queue).filter_by(status='waiting').order_by(
            Queue.priority_score.desc(),
            Queue.created_at.asc()
        ).all()
        
        queue_data = []
        for entry in queue_entries:
            queue_data.append({
                'id': entry.id,
                'citizen_name': f"{entry.citizen.first_name} {entry.citizen.last_name}",
                'service_type': entry.service_type.name,
                'ticket_number': entry.ticket_number,
                'priority_score': entry.priority_score,
                'created_at': entry.created_at.isoformat(),
                'estimated_wait_time': getattr(entry, 'estimated_wait_time', None)
            })
        
        # Get agent status
        agents = session.query(Agent).all()
        agent_data = []
        for agent in agents:
            agent_info = {
                'id': agent.id,
                'name': getattr(agent, 'name', f'Agent {agent.id}'),
                'counter_number': getattr(agent, 'counter_number', agent.id),
                'status': agent.status
            }
            
            # Find current citizen being served by this agent
            current_queue_entry = session.query(Queue).filter_by(
                agent_id=agent.id,
                status='in_progress'
            ).first()
            
            if current_queue_entry:
                current_citizen = current_queue_entry.citizen
                agent_info['current_citizen'] = f"{current_citizen.first_name} {current_citizen.last_name}"
            
            agent_data.append(agent_info)
        
        return jsonify({
            'queue': queue_data,
            'agents': agent_data,
            'total_waiting': len(queue_data)
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Error retrieving queue: {str(e)}'}), 500
