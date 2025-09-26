from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

from ..queue_logic.performance_monitor import (
    metrics_collector, audit_manager, performance_dashboard,
    MetricType, AlertLevel
)
from ..auth.decorators import admin_required

logger = logging.getLogger(__name__)

performance_bp = Blueprint('performance', __name__, url_prefix='/api/performance')

@performance_bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    """Get real-time performance dashboard data"""
    try:
        dashboard_data = performance_dashboard.get_dashboard_data()
        
        # Log access for audit
        audit_manager.log_event(
            event_type='dashboard_access',
            entity_type='performance_dashboard',
            entity_id=None,
            user_id=current_user.id,
            action='view_dashboard',
            details={'endpoint': '/api/performance/dashboard'},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve dashboard data'
        }), 500

@performance_bp.route('/metrics', methods=['GET'])
@login_required
def get_metrics():
    """Get performance metrics with optional filtering"""
    try:
        # Parse query parameters
        metric_type_str = request.args.get('type')
        last_minutes = int(request.args.get('last_minutes', 30))
        
        metric_type = None
        if metric_type_str:
            try:
                metric_type = MetricType(metric_type_str)
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': f'Invalid metric type: {metric_type_str}'
                }), 400
        
        metrics = metrics_collector.get_current_metrics(
            metric_type=metric_type,
            last_n_minutes=last_minutes
        )
        
        # Convert to JSON-serializable format
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                'type': metric.metric_type.value,
                'name': metric.name,
                'value': metric.value,
                'unit': metric.unit,
                'timestamp': metric.timestamp.isoformat(),
                'metadata': metric.metadata,
                'threshold_warning': metric.threshold_warning,
                'threshold_critical': metric.threshold_critical
            })
        
        # Log access
        audit_manager.log_event(
            event_type='metrics_access',
            entity_type='performance_metrics',
            entity_id=None,
            user_id=current_user.id,
            action='view_metrics',
            details={
                'metric_type': metric_type_str,
                'last_minutes': last_minutes,
                'metrics_count': len(metrics_data)
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'data': {
                'metrics': metrics_data,
                'total_count': len(metrics_data),
                'time_range_minutes': last_minutes
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve metrics'
        }), 500

@performance_bp.route('/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get active performance alerts"""
    try:
        active_alerts = metrics_collector.get_active_alerts()
        
        alerts_data = []
        for alert in active_alerts:
            alerts_data.append({
                'id': alert.alert_id,
                'level': alert.level.value,
                'metric_name': alert.metric_name,
                'current_value': alert.current_value,
                'threshold_value': alert.threshold_value,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved,
                'resolution_timestamp': alert.resolution_timestamp.isoformat() if alert.resolution_timestamp else None
            })
        
        # Log access
        audit_manager.log_event(
            event_type='alerts_access',
            entity_type='performance_alerts',
            entity_id=None,
            user_id=current_user.id,
            action='view_alerts',
            details={'active_alerts_count': len(alerts_data)},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'data': {
                'alerts': alerts_data,
                'total_count': len(alerts_data)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve alerts'
        }), 500

@performance_bp.route('/alerts/<alert_id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_alert(alert_id):
    """Resolve a performance alert"""
    try:
        metrics_collector.resolve_alert(alert_id)
        
        # Log resolution
        audit_manager.log_event(
            event_type='alert_resolution',
            entity_type='performance_alert',
            entity_id=None,
            user_id=current_user.id,
            action='resolve_alert',
            details={'alert_id': alert_id},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Alert {alert_id} resolved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to resolve alert'
        }), 500

@performance_bp.route('/audit', methods=['GET'])
@login_required
@admin_required
def get_audit_trail():
    """Get audit trail with optional filtering"""
    try:
        # Parse query parameters
        entity_type = request.args.get('entity_type')
        entity_id = request.args.get('entity_id', type=int)
        user_id = request.args.get('user_id', type=int)
        limit = int(request.args.get('limit', 100))
        
        # Parse time range
        start_time = None
        end_time = None
        
        if request.args.get('start_time'):
            start_time = datetime.fromisoformat(request.args.get('start_time'))
        if request.args.get('end_time'):
            end_time = datetime.fromisoformat(request.args.get('end_time'))
        
        # Default to last 24 hours if no time range specified
        if not start_time and not end_time:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
        
        audit_entries = audit_manager.get_audit_trail(
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        # Convert to JSON-serializable format
        audit_data = []
        for entry in audit_entries:
            audit_data.append({
                'timestamp': entry.timestamp.isoformat(),
                'event_type': entry.event_type,
                'entity_type': entry.entity_type,
                'entity_id': entry.entity_id,
                'user_id': entry.user_id,
                'action': entry.action,
                'details': entry.details,
                'ip_address': entry.ip_address,
                'user_agent': entry.user_agent,
                'session_id': entry.session_id
            })
        
        # Log audit access
        audit_manager.log_event(
            event_type='audit_access',
            entity_type='audit_trail',
            entity_id=None,
            user_id=current_user.id,
            action='view_audit_trail',
            details={
                'filters': {
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'user_id': user_id,
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None
                },
                'results_count': len(audit_data)
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'data': {
                'audit_entries': audit_data,
                'total_count': len(audit_data),
                'filters_applied': {
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'user_id': user_id,
                    'start_time': start_time.isoformat() if start_time else None,
                    'end_time': end_time.isoformat() if end_time else None
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting audit trail: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve audit trail'
        }), 500

@performance_bp.route('/report', methods=['POST'])
@login_required
@admin_required
def generate_report():
    """Generate performance report for specified time range"""
    try:
        data = request.get_json()
        
        if not data or 'start_time' not in data or 'end_time' not in data:
            return jsonify({
                'success': False,
                'error': 'start_time and end_time are required'
            }), 400
        
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        
        if start_time >= end_time:
            return jsonify({
                'success': False,
                'error': 'start_time must be before end_time'
            }), 400
        
        report = performance_dashboard.generate_performance_report(
            start_time, end_time
        )
        
        # Log report generation
        audit_manager.log_event(
            event_type='report_generation',
            entity_type='performance_report',
            entity_id=None,
            user_id=current_user.id,
            action='generate_report',
            details={
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'report_metrics_count': report.get('total_metrics', 0)
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'data': report
        })
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate report'
        }), 500

@performance_bp.route('/monitoring/status', methods=['GET'])
@login_required
def get_monitoring_status():
    """Get monitoring system status"""
    try:
        status = {
            'monitoring_active': metrics_collector._running,
            'collection_interval': metrics_collector.collection_interval,
            'metrics_buffer_size': len(metrics_collector.metrics_buffer),
            'audit_buffer_size': len(audit_manager.audit_buffer),
            'active_alerts_count': len(metrics_collector.get_active_alerts()),
            'last_collection_time': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve monitoring status'
        }), 500

@performance_bp.route('/monitoring/restart', methods=['POST'])
@login_required
@admin_required
def restart_monitoring():
    """Restart the monitoring system"""
    try:
        metrics_collector.stop_monitoring()
        metrics_collector.start_monitoring()
        
        # Log restart
        audit_manager.log_event(
            event_type='system_control',
            entity_type='monitoring_system',
            entity_id=None,
            user_id=current_user.id,
            action='restart_monitoring',
            details={'timestamp': datetime.now().isoformat()},
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': 'Monitoring system restarted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error restarting monitoring: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to restart monitoring system'
        }), 500

# Error handlers
@performance_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@performance_bp.route('/dashboard/view', methods=['GET'])
@login_required
def view_dashboard():
    """Serve the performance dashboard HTML page"""
    return render_template('performance_dashboard.html')

@performance_bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500