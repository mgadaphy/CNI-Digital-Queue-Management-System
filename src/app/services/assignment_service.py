from ..models import db, Queue, Agent, SystemConfig
from datetime import datetime
from flask import current_app

def assign_next_ticket(ticket_id):
    """
    Attempt to assign a specific ticket to the best available agent.
    Returns result dict similar to API response structure.
    """
    try:
        # 1. Validation
        ticket = Queue.query.get(ticket_id)
        if not ticket or ticket.status != 'waiting':
            return {'success': False, 'message': 'Invalid ticket'}

        # 2. Check Global Auto-Assign Config
        config = SystemConfig.query.get('auto_assign_enabled')
        if config and config.value == 'false':
            return {'success': False, 'message': 'Auto-assign disabled'}

        # 3. Find Available Agent (Exclude Admin)
        agents = Agent.query.filter(
            Agent.status == 'available',
            Agent.is_active == True,
            Agent.role != 'admin'
        ).all()
        
        if not agents:
            return {'success': False, 'message': 'No agents available'}

        # 4. Load Balancing (Fewest tickets)
        best_agent = min(agents, key=lambda a: Queue.query.filter(
            Queue.agent_id == a.id,
            Queue.status.in_(['assigned', 'waiting', 'in_progress'])
        ).count())

        # 5. Check Capacity
        current_load = Queue.query.filter_by(agent_id=best_agent.id, status='in_progress').count()
        if current_load >= getattr(best_agent, 'max_concurrent_tickets', 3):
            return {'success': False, 'message': 'Agent at capacity'}

        # 6. Assign
        ticket.agent_id = best_agent.id
        ticket.status = 'assigned'
        ticket.updated_at = datetime.utcnow()
        db.session.commit()

        # 7. Notify (Simulated return, calling code handles actual notification/logging if needed)
        return {
            'success': True, 
            'ticket': ticket, 
            'agent': best_agent
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Auto-assign error: {e}")
        return {'success': False, 'message': str(e)}

def trigger_batch_assignment():
    """
    Trigger assignment for all waiting tickets.
    """
    waiting_tickets = Queue.query.filter_by(status='waiting').order_by(
        Queue.priority_score.desc(), 
        Queue.created_at
    ).all()
    
    results = []
    for ticket in waiting_tickets:
        res = assign_next_ticket(ticket.id)
        if res['success']:
            results.append(res)
    return results
