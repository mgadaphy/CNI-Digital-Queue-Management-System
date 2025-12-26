@admin_bp.route('/api/metrics/dashboard')
@login_required
def dashboard_metrics():
    """Get dashboard metrics for AJAX updates"""
    try:
        today = datetime.utcnow().date()
        
        # 1. Current Metrics
        queue_waiting = Queue.query.filter_by(status='waiting').count()
        queue_in_progress = Queue.query.filter_by(status='in_progress').count()
        queue_completed_today = Queue.query.filter(
            Queue.status == 'completed',
            func.date(Queue.updated_at) == today
        ).count()
        
        # Avg Wait Time
        avg_wait_seconds = db.session.query(
            func.avg(func.strftime('%s', Queue.called_at) - func.strftime('%s', Queue.created_at))
        ).filter(
            Queue.status == 'completed',
            Queue.called_at.isnot(None),
            func.date(Queue.updated_at) == today
        ).scalar()
        average_wait_time = round(avg_wait_seconds / 60) if avg_wait_seconds else 0
        
        # Avg Service Time
        avg_service_seconds = db.session.query(
            func.avg(Queue.service_time)
        ).filter(
            Queue.status == 'completed',
            func.date(Queue.updated_at) == today
        ).scalar()
        average_service_time = round(avg_service_seconds) if avg_service_seconds else 0

        # Agent Utilization (Active / Total Agents)
        total_agents = Agent.query.filter(Agent.role != 'admin').count()
        active_agents = Agent.query.filter(
            Agent.role != 'admin',
            Agent.status.in_(['available', 'busy'])
        ).count()
        agent_utilization = round((active_agents / total_agents * 100) if total_agents > 0 else 0)

        # 2. Hourly Distribution (Tickets created per hour today)
        hourly_data = db.session.query(
            func.strftime('%H', Queue.created_at).label('hour'),
            func.count(Queue.id).label('count')
        ).filter(
            func.date(Queue.created_at) == today
        ).group_by('hour').all()
        
        hourly_distribution = [{'hour': int(h), 'tickets': c} for h, c in hourly_data]
        
        # 3. Service Distribution (Tickets per service today)
        service_data = db.session.query(
            ServiceType.name_fr,
            func.count(Queue.id)
        ).join(Queue).filter(
            func.date(Queue.created_at) == today
        ).group_by(ServiceType.name_fr).all()
        
        service_distribution = {name: count for name, count in service_data}
        
        return jsonify({
            'success': True,
            'data': {
                'current_metrics': {
                    'queue_waiting': queue_waiting,
                    'queue_in_progress': queue_in_progress,
                    'queue_completed_today': queue_completed_today,
                    'average_wait_time': average_wait_time,
                    'average_service_time': average_service_time,
                    'agent_utilization': agent_utilization
                },
                'hourly_distribution': hourly_distribution,
                'service_distribution': service_distribution,
                'alerts': [] # Placeholder for alerts system
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching dashboard metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
