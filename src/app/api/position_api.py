from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging

from ..queue_logic.position_tracker import get_position_tracker, refresh_queue_positions, get_queue_position
from ..models import Queue, Agent
from ..auth.decorators import admin_required, agent_required

logger = logging.getLogger(__name__)

position_api_bp = Blueprint('position_api', __name__)

@position_api_bp.route('/positions', methods=['GET'])
@jwt_required()
def get_all_positions():
    """Get all current queue positions"""
    try:
        tracker = get_position_tracker()
        positions = tracker.get_current_positions()
        statistics = tracker.get_statistics()
        
        # Get detailed position data
        position_details = []
        for entry_id, position in positions.items():
            entry = Queue.query.get(entry_id)
            if entry:
                position_details.append({
                    'entry_id': entry_id,
                    'position': position,
                    'customer_name': entry.customer_name,
                    'service_type': entry.service_type,
                    'priority_score': entry.priority_score,
                    'created_at': entry.created_at.isoformat(),
                    'estimated_wait_time': tracker._calculate_estimated_wait_time(position)
                })
        
        # Sort by position
        position_details.sort(key=lambda x: x['position'])
        
        return jsonify({
            'success': True,
            'positions': position_details,
            'statistics': statistics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting positions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving positions: {str(e)}'
        }), 500

@position_api_bp.route('/positions/<int:entry_id>', methods=['GET'])
@jwt_required()
def get_entry_position(entry_id):
    """Get position for a specific queue entry"""
    try:
        position = get_queue_position(entry_id)
        
        if position is None:
            return jsonify({
                'success': False,
                'message': 'Entry not found in waiting queue'
            }), 404
        
        # Get entry details
        entry = Queue.query.get(entry_id)
        if not entry:
            return jsonify({
                'success': False,
                'message': 'Queue entry not found'
            }), 404
        
        tracker = get_position_tracker()
        estimated_wait = tracker._calculate_estimated_wait_time(position)
        
        return jsonify({
            'success': True,
            'entry_id': entry_id,
            'position': position,
            'customer_name': entry.customer_name,
            'service_type': entry.service_type,
            'priority_score': entry.priority_score,
            'estimated_wait_time': estimated_wait,
            'status': entry.status,
            'created_at': entry.created_at.isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting entry position: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving entry position: {str(e)}'
        }), 500

@position_api_bp.route('/positions/refresh', methods=['POST'])
@jwt_required()
@agent_required
def refresh_positions():
    """Manually refresh all queue positions"""
    try:
        result = refresh_queue_positions()
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Queue positions refreshed successfully',
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to refresh positions',
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        logger.error(f"Error refreshing positions: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error refreshing positions: {str(e)}'
        }), 500

@position_api_bp.route('/positions/statistics', methods=['GET'])
@jwt_required()
@agent_required
def get_position_statistics():
    """Get position tracker statistics"""
    try:
        tracker = get_position_tracker()
        statistics = tracker.get_statistics()
        
        # Add additional queue statistics
        total_waiting = Queue.query.filter_by(status='waiting').count()
        total_being_served = Queue.query.filter_by(status='being_served').count()
        total_completed_today = Queue.query.filter(
            Queue.status == 'completed',
            Queue.updated_at >= tracker.last_update.date() if tracker.last_update else None
        ).count() if tracker.last_update else 0
        
        active_agents = Agent.query.filter_by(status='available').count()
        
        enhanced_statistics = {
            **statistics,
            'queue_summary': {
                'total_waiting': total_waiting,
                'total_being_served': total_being_served,
                'total_completed_today': total_completed_today,
                'active_agents': active_agents
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': enhanced_statistics
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving statistics: {str(e)}'
        }), 500

@position_api_bp.route('/positions/customer/<int:entry_id>/notify', methods=['POST'])
@jwt_required()
@agent_required
def notify_customer_position(entry_id):
    """Send position notification to a specific customer"""
    try:
        position = get_queue_position(entry_id)
        
        if position is None:
            return jsonify({
                'success': False,
                'message': 'Entry not found in waiting queue'
            }), 404
        
        entry = Queue.query.get(entry_id)
        if not entry:
            return jsonify({
                'success': False,
                'message': 'Queue entry not found'
            }), 404
        
        tracker = get_position_tracker()
        estimated_wait = tracker._calculate_estimated_wait_time(position)
        
        # Emit individual notification
        from ..extensions import socketio
        socketio.emit('position_notification', {
            'entry_id': entry_id,
            'customer_name': entry.customer_name,
            'current_position': position,
            'estimated_wait_time': estimated_wait,
            'message': f'You are currently #{position} in the queue. Estimated wait time: {estimated_wait} minutes.',
            'timestamp': tracker.last_update.isoformat() if tracker.last_update else None
        }, room=f"customer_{entry_id}")
        
        return jsonify({
            'success': True,
            'message': f'Position notification sent to {entry.customer_name}',
            'position': position,
            'estimated_wait_time': estimated_wait
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending position notification: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error sending notification: {str(e)}'
        }), 500

@position_api_bp.route('/positions/broadcast', methods=['POST'])
@jwt_required()
@admin_required
def broadcast_position_update():
    """Broadcast position update to all clients"""
    try:
        data = request.get_json() or {}
        message = data.get('message', 'Queue positions have been updated')
        
        tracker = get_position_tracker()
        
        # Force a position refresh and broadcast
        result = tracker.refresh_positions()
        
        if result['success']:
            # Additional broadcast with custom message
            from ..utils.websocket_utils import emit_queue_update
            emit_queue_update(
                message,
                update_type='manual_broadcast',
                data={
                    'total_entries': result['total_entries'],
                    'broadcast_by': get_jwt_identity(),
                    'timestamp': result['timestamp']
                }
            )
            
            return jsonify({
                'success': True,
                'message': 'Position update broadcasted successfully',
                'data': result
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to broadcast position update',
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        logger.error(f"Error broadcasting position update: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error broadcasting update: {str(e)}'
        }), 500