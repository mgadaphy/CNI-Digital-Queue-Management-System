from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.queue_logger import get_queue_logger
from ..utils.db_transaction_manager import get_transaction_manager
from ..utils.performance_metrics import get_performance_collector, take_performance_snapshot
from ..models import Queue, Agent, Citizen, ServiceType
from ..extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, and_
import json
import os

monitoring_api_bp = Blueprint('monitoring_api', __name__)

@monitoring_api_bp.route('/statistics', methods=['GET'])
@jwt_required()
def get_queue_statistics():
    """Get comprehensive queue statistics"""
    try:
        hours = request.args.get('hours', 24, type=int)
        queue_logger = get_queue_logger()
        
        # Get statistics from logger
        stats = queue_logger.get_queue_statistics(hours)
        
        # Add real-time queue status
        current_waiting = db.session.query(Queue).filter_by(status='waiting').count()
        current_in_progress = db.session.query(Queue).filter_by(status='in_progress').count()
        
        # Get agent statistics
        total_agents = db.session.query(Agent).count()
        available_agents = db.session.query(Agent).filter_by(status='available').count()
        busy_agents = db.session.query(Agent).filter_by(status='busy').count()
        
        # Get service type distribution
        service_distribution = db.session.query(
            ServiceType.name,
            func.count(Queue.id).label('count')
        ).join(Queue).filter(
            Queue.created_at >= datetime.utcnow() - timedelta(hours=hours)
        ).group_by(ServiceType.name).all()
        
        stats.update({
            'current_status': {
                'waiting': current_waiting,
                'in_progress': current_in_progress,
                'total_agents': total_agents,
                'available_agents': available_agents,
                'busy_agents': busy_agents
            },
            'service_distribution': [
                {'service_type': name, 'count': count} 
                for name, count in service_distribution
            ]
        })
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_queue_statistics'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving statistics: {str(e)}'
        }), 500

@monitoring_api_bp.route('/performance-metrics', methods=['GET'])
@jwt_required()
def get_performance_metrics():
    """Get performance metrics from log files"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # Read performance log file
        log_file_path = 'logs/queue_performance.log'
        
        if not os.path.exists(log_file_path):
            return jsonify({
                'success': True,
                'metrics': [],
                'message': 'No performance data available yet'
            }), 200
        
        metrics = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with open(log_file_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    log_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    
                    if log_time >= cutoff_time:
                        metrics.append({
                            'timestamp': log_entry['timestamp'],
                            'operation': log_entry['operation'],
                            'duration_ms': log_entry['duration_ms'],
                            'additional_data': log_entry.get('additional_data', {})
                        })
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        # Calculate aggregated metrics
        operation_stats = {}
        for metric in metrics:
            op = metric['operation']
            if op not in operation_stats:
                operation_stats[op] = {
                    'count': 0,
                    'total_duration': 0,
                    'min_duration': float('inf'),
                    'max_duration': 0
                }
            
            stats = operation_stats[op]
            duration = metric['duration_ms']
            
            stats['count'] += 1
            stats['total_duration'] += duration
            stats['min_duration'] = min(stats['min_duration'], duration)
            stats['max_duration'] = max(stats['max_duration'], duration)
        
        # Calculate averages
        for op, stats in operation_stats.items():
            if stats['count'] > 0:
                stats['avg_duration'] = round(stats['total_duration'] / stats['count'], 2)
                if stats['min_duration'] == float('inf'):
                    stats['min_duration'] = 0
        
        return jsonify({
            'success': True,
            'metrics': {
                'raw_metrics': metrics[-100:],  # Last 100 entries
                'aggregated_stats': operation_stats,
                'total_operations': len(metrics)
            }
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_performance_metrics'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving performance metrics: {str(e)}'
        }), 500

@monitoring_api_bp.route('/error-logs', methods=['GET'])
@jwt_required()
def get_error_logs():
    """Get recent error logs"""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        # Read error log file
        log_file_path = 'logs/queue_errors.log'
        
        if not os.path.exists(log_file_path):
            return jsonify({
                'success': True,
                'errors': [],
                'message': 'No error logs available'
            }), 200
        
        errors = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with open(log_file_path, 'r') as f:
            for line in f:
                try:
                    log_entry = json.loads(line.strip())
                    log_time = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))
                    
                    if log_time >= cutoff_time:
                        # Remove full traceback for API response (too verbose)
                        error_summary = {
                            'timestamp': log_entry['timestamp'],
                            'error_type': log_entry['error_type'],
                            'error_message': log_entry['error_message'],
                            'context': log_entry.get('context', {}),
                            'request_id': log_entry.get('request_id'),
                            'user_id': log_entry.get('user_id')
                        }
                        errors.append(error_summary)
                        
                        if len(errors) >= limit:
                            break
                            
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
        
        # Sort by timestamp (most recent first)
        errors.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'errors': errors,
            'total_errors': len(errors)
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_error_logs'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving error logs: {str(e)}'
        }), 500

@monitoring_api_bp.route('/health-check', methods=['GET'])
def health_check():
    """System health check endpoint"""
    try:
        # Check database connectivity
        db.session.execute('SELECT 1')
        db_status = 'healthy'
        
        # Check queue status
        queue_count = db.session.query(Queue).filter_by(status='waiting').count()
        
        # Check agent availability
        available_agents = db.session.query(Agent).filter_by(status='available').count()
        total_agents = db.session.query(Agent).count()
        
        # Determine overall health
        health_status = 'healthy'
        issues = []
        
        if available_agents == 0 and total_agents > 0:
            health_status = 'warning'
            issues.append('No agents available')
        
        if queue_count > 100:  # Arbitrary threshold
            health_status = 'warning'
            issues.append(f'High queue volume: {queue_count} waiting')
        
        return jsonify({
            'status': health_status,
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': db_status,
                'queue_system': 'operational'
            },
            'metrics': {
                'waiting_queue_count': queue_count,
                'available_agents': available_agents,
                'total_agents': total_agents
            },
            'issues': issues
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@monitoring_api_bp.route('/system-info', methods=['GET'])
@jwt_required()
def get_system_info():
    """Get system information and configuration"""
    try:
        from ..queue_logic.queue_config import get_queue_config
        
        config = get_queue_config()
        
        # Get transaction manager stats if available
        transaction_manager = get_transaction_manager()
        tx_stats = transaction_manager.get_statistics() if hasattr(transaction_manager, 'get_statistics') else {}
        
        return jsonify({
            'success': True,
            'system_info': {
                'queue_config': {
                    'optimization_interval': config.OPTIMIZATION_INTERVAL_MINUTES,
                    'batch_size': config.OPTIMIZATION_BATCH_SIZE,
                    'priority_weights': {
                        'wait_time': config.WAIT_TIME_WEIGHT,
                        'service_complexity': config.SERVICE_COMPLEXITY_WEIGHT,
                        'citizen_priority': config.CITIZEN_PRIORITY_WEIGHT
                    },
                    'thresholds': {
                        'high_priority': config.HIGH_PRIORITY_THRESHOLD,
                        'reoptimization': config.REOPTIMIZATION_THRESHOLD
                    }
                },
                'transaction_stats': tx_stats,
                'logging_enabled': True,
                'monitoring_enabled': True
            }
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_system_info'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving system info: {str(e)}'
        }), 500

@monitoring_api_bp.route('/performance/snapshot', methods=['GET'])
@jwt_required()
def get_performance_snapshot():
    """Get current queue performance snapshot"""
    try:
        snapshot = take_performance_snapshot()
        
        return jsonify({
            'success': True,
            'snapshot': {
                'timestamp': snapshot.timestamp.isoformat(),
                'total_queue_length': snapshot.total_queue_length,
                'average_wait_time': snapshot.average_wait_time,
                'service_efficiency': snapshot.service_efficiency,
                'agent_utilization': snapshot.agent_utilization,
                'optimization_score': snapshot.optimization_score,
                'active_agents': snapshot.active_agents,
                'completed_services': snapshot.completed_services,
                'priority_distribution': snapshot.priority_distribution
            }
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_performance_snapshot'})
        return jsonify({
            'success': False,
            'message': f'Error taking performance snapshot: {str(e)}'
        }), 500

@monitoring_api_bp.route('/performance/summary', methods=['GET'])
@jwt_required()
def get_performance_summary():
    """Get performance summary for specified time period"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        performance_collector = get_performance_collector()
        summary = performance_collector.get_performance_summary(hours)
        
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_performance_summary'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving performance summary: {str(e)}'
        }), 500

@monitoring_api_bp.route('/performance/optimization', methods=['GET'])
@jwt_required()
def get_optimization_analytics():
    """Get detailed optimization performance analytics"""
    try:
        performance_collector = get_performance_collector()
        analytics = performance_collector.get_optimization_analytics()
        
        return jsonify({
            'success': True,
            'analytics': analytics
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_optimization_analytics'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving optimization analytics: {str(e)}'
        }), 500

@monitoring_api_bp.route('/performance/realtime', methods=['GET'])
@jwt_required()
def get_realtime_metrics():
    """Get real-time performance metrics"""
    try:
        metric_names = request.args.getlist('metrics')
        
        performance_collector = get_performance_collector()
        metrics = performance_collector.get_real_time_metrics(metric_names if metric_names else None)
        
        # Format timestamps for JSON serialization
        formatted_metrics = {}
        for name, data_points in metrics.items():
            formatted_metrics[name] = [
                {'timestamp': ts.isoformat(), 'value': value}
                for ts, value in data_points
            ]
        
        return jsonify({
            'success': True,
            'metrics': formatted_metrics,
            'available_metrics': list(metrics.keys())
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_realtime_metrics'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving real-time metrics: {str(e)}'
        }), 500

@monitoring_api_bp.route('/performance/cleanup', methods=['POST'])
@jwt_required()
def cleanup_performance_data():
    """Clean up old performance data"""
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 168)  # Default: 1 week
        
        performance_collector = get_performance_collector()
        performance_collector.clear_old_data(hours)
        
        queue_logger = get_queue_logger()
        queue_logger.log_queue_event('performance_data_cleanup', {
            'hours_retained': hours,
            'cleaned_by': get_jwt_identity()
        })
        
        return jsonify({
            'success': True,
            'message': f'Performance data older than {hours} hours has been cleaned up'
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'cleanup_performance_data'})
        return jsonify({
            'success': False,
            'message': f'Error cleaning up performance data: {str(e)}'
        }), 500