import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
from flask import request, g
from sqlalchemy import event
from ..extensions import db
from ..models import Queue, Agent, Citizen
import traceback
import time

class QueueLogger:
    """Comprehensive logging system for queue operations"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = None
        self.performance_logger = None
        self.error_logger = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize logging with Flask app"""
        self.app = app
        
        # Configure main queue logger
        self.logger = logging.getLogger('queue_operations')
        self.logger.setLevel(logging.INFO)
        
        # Configure performance logger
        self.performance_logger = logging.getLogger('queue_performance')
        self.performance_logger.setLevel(logging.INFO)
        
        # Configure error logger
        self.error_logger = logging.getLogger('queue_errors')
        self.error_logger.setLevel(logging.ERROR)
        
        # Create formatters
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create file handlers with directory creation
        import os
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        queue_handler = logging.FileHandler('logs/queue_operations.log')
        queue_handler.setFormatter(formatter)
        self.logger.addHandler(queue_handler)
        
        performance_handler = logging.FileHandler('logs/queue_performance.log')
        performance_handler.setFormatter(formatter)
        self.performance_logger.addHandler(performance_handler)
        
        error_handler = logging.FileHandler('logs/queue_errors.log')
        error_handler.setFormatter(formatter)
        self.error_logger.addHandler(error_handler)
        
        # Setup database event listeners
        self._setup_db_listeners()
        
        # Store logger instance in app
        app.queue_logger = self
    
    def _setup_db_listeners(self):
        """Setup SQLAlchemy event listeners for queue operations"""
        
        @event.listens_for(Queue, 'after_insert')
        def log_queue_insert(mapper, connection, target):
            self.log_queue_event('queue_entry_created', {
                'queue_id': target.id,
                'citizen_id': target.citizen_id,
                'service_type_id': target.service_type_id,
                'priority_score': target.priority_score,
                'status': target.status
            })
        
        @event.listens_for(Queue, 'after_update')
        def log_queue_update(mapper, connection, target):
            self.log_queue_event('queue_entry_updated', {
                'queue_id': target.id,
                'citizen_id': target.citizen_id,
                'status': target.status,
                'agent_id': target.agent_id,
                'called_at': target.called_at.isoformat() if target.called_at else None,
                'completed_at': target.completed_at.isoformat() if target.completed_at else None
            })
        
        @event.listens_for(Agent, 'after_update')
        def log_agent_update(mapper, connection, target):
            # Get current citizen through active ticket
            current_citizen_id = None
            try:
                from ..models import Queue
                current_ticket = Queue.query.filter_by(
                    agent_id=target.id, 
                    status='in_progress'
                ).first()
                if current_ticket:
                    current_citizen_id = current_ticket.citizen_id
            except Exception:
                # If we can't get the current citizen, just log None
                pass
                
            self.log_queue_event('agent_status_changed', {
                'agent_id': target.id,
                'status': target.status,
                'current_citizen_id': current_citizen_id
            })
    
    def log_queue_event(self, event_type: str, data: Dict[str, Any], level: str = 'info'):
        """Log queue-related events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'data': data,
            'request_id': getattr(g, 'request_id', None),
            'user_id': getattr(g, 'user_id', None)
        }
        
        message = json.dumps(log_entry)
        
        if level == 'error':
            self.error_logger.error(message)
        elif level == 'warning':
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def log_performance_metric(self, operation: str, duration: float, 
                             additional_data: Optional[Dict[str, Any]] = None):
        """Log performance metrics"""
        metric_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'request_id': getattr(g, 'request_id', None),
            'additional_data': additional_data or {}
        }
        
        self.performance_logger.info(json.dumps(metric_entry))
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log errors with context"""
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {},
            'request_id': getattr(g, 'request_id', None),
            'user_id': getattr(g, 'user_id', None)
        }
        
        self.error_logger.error(json.dumps(error_entry))
    
    def get_queue_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get queue operation statistics"""
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get queue statistics
            total_entries = db.session.query(Queue).filter(
                Queue.created_at >= cutoff_time
            ).count()
            
            completed_entries = db.session.query(Queue).filter(
                Queue.created_at >= cutoff_time,
                Queue.status == 'completed'
            ).count()
            
            waiting_entries = db.session.query(Queue).filter(
                Queue.status.in_(['waiting', 'assigned'])
            ).count()
            
            in_progress_entries = db.session.query(Queue).filter(
                Queue.status == 'in_progress'
            ).count()
            
            # Calculate average wait time for completed entries
            completed_with_times = db.session.query(Queue).filter(
                Queue.created_at >= cutoff_time,
                Queue.status == 'completed',
                Queue.called_at.isnot(None),
                Queue.completed_at.isnot(None)
            ).all()
            
            avg_wait_time = 0
            avg_service_time = 0
            
            if completed_with_times:
                wait_times = [(entry.called_at - entry.created_at).total_seconds() 
                            for entry in completed_with_times if entry.called_at]
                service_times = [(entry.completed_at - entry.called_at).total_seconds() 
                               for entry in completed_with_times if entry.completed_at and entry.called_at]
                
                avg_wait_time = sum(wait_times) / len(wait_times) if wait_times else 0
                avg_service_time = sum(service_times) / len(service_times) if service_times else 0
            
            return {
                'period_hours': hours,
                'total_entries': total_entries,
                'completed_entries': completed_entries,
                'waiting_entries': waiting_entries,
                'in_progress_entries': in_progress_entries,
                'completion_rate': (completed_entries / total_entries * 100) if total_entries > 0 else 0,
                'avg_wait_time_seconds': round(avg_wait_time, 2),
                'avg_service_time_seconds': round(avg_service_time, 2)
            }
            
        except Exception as e:
            self.log_error(e, {'operation': 'get_queue_statistics'})
            return {}


def performance_monitor(operation_name: str):
    """Decorator to monitor performance of queue operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log successful operation
                if hasattr(g, 'queue_logger'):
                    g.queue_logger.log_performance_metric(
                        operation_name, 
                        duration,
                        {'success': True, 'args_count': len(args), 'kwargs_count': len(kwargs)}
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log failed operation
                if hasattr(g, 'queue_logger'):
                    g.queue_logger.log_performance_metric(
                        operation_name, 
                        duration,
                        {'success': False, 'error': str(e)}
                    )
                    g.queue_logger.log_error(e, {
                        'operation': operation_name,
                        'args': str(args)[:200],  # Limit length
                        'kwargs': str(kwargs)[:200]
                    })
                
                raise
        
        return wrapper
    return decorator


def queue_operation_logger(operation_type: str):
    """Decorator to log queue operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Log operation start
            if hasattr(g, 'queue_logger'):
                g.queue_logger.log_queue_event(f'{operation_type}_started', {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                })
            
            try:
                result = func(*args, **kwargs)
                
                # Log operation success
                if hasattr(g, 'queue_logger'):
                    g.queue_logger.log_queue_event(f'{operation_type}_completed', {
                        'function': func.__name__,
                        'success': True
                    })
                
                return result
                
            except Exception as e:
                # Log operation failure
                if hasattr(g, 'queue_logger'):
                    g.queue_logger.log_queue_event(f'{operation_type}_failed', {
                        'function': func.__name__,
                        'error': str(e)
                    }, level='error')
                
                raise
        
        return wrapper
    return decorator


# Global logger instance
_queue_logger = None

def get_queue_logger(app=None):
    """Get or create queue logger instance"""
    global _queue_logger
    
    if _queue_logger is None:
        _queue_logger = QueueLogger(app)
    elif app is not None and _queue_logger.app is None:
        _queue_logger.init_app(app)
    
    return _queue_logger