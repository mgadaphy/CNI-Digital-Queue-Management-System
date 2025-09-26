import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from flask import current_app
from sqlalchemy import event
from sqlalchemy.orm import Session

from ..models import Queue, db
from ..extensions import socketio
from .queue_config import get_queue_config
from ..utils.websocket_utils import emit_queue_update

logger = logging.getLogger(__name__)

class QueuePositionTracker:
    """Tracks and broadcasts real-time queue position updates"""
    
    def __init__(self):
        self.config = get_queue_config()
        self.position_cache = {}  # Cache for current positions
        self.last_update = None
        self.update_count = 0
        
        # Register database event listeners
        self._register_db_listeners()
    
    def _register_db_listeners(self):
        """Register SQLAlchemy event listeners for queue changes"""
        
        @event.listens_for(Queue, 'after_insert')
        def queue_entry_inserted(mapper, connection, target):
            """Handle new queue entry insertion"""
            if target.status == 'waiting':
                self._handle_queue_change('insert', target)
        
        @event.listens_for(Queue, 'after_update')
        def queue_entry_updated(mapper, connection, target):
            """Handle queue entry updates"""
            # Check if status changed to/from waiting
            if hasattr(target, '_sa_instance_state'):
                history = target._sa_instance_state.get_history('status', True)
                if history.has_changes():
                    old_status = history.deleted[0] if history.deleted else None
                    new_status = target.status
                    
                    if old_status != new_status:
                        if new_status == 'waiting' or old_status == 'waiting':
                            self._handle_queue_change('update', target, old_status)
            
            # Check if priority changed for waiting entries
            if target.status == 'waiting':
                priority_history = target._sa_instance_state.get_history('priority_score', True)
                if priority_history.has_changes():
                    self._handle_queue_change('priority_update', target)
        
        @event.listens_for(Queue, 'after_delete')
        def queue_entry_deleted(mapper, connection, target):
            """Handle queue entry deletion"""
            if target.status == 'waiting':
                self._handle_queue_change('delete', target)
    
    def _handle_queue_change(self, change_type: str, entry: Queue, old_status: Optional[str] = None):
        """Handle queue changes and trigger position updates"""
        try:
            logger.debug(f"Queue change detected: {change_type} for entry {entry.id}")
            
            # Update position cache and broadcast changes
            self._update_positions_and_broadcast(change_type, entry, old_status)
            
        except Exception as e:
            logger.error(f"Error handling queue change: {str(e)}")
    
    def _update_positions_and_broadcast(self, change_type: str, entry: Queue, old_status: Optional[str] = None):
        """Update position cache and broadcast changes to clients"""
        try:
            # Get current waiting queue ordered by priority
            waiting_entries = Queue.query.filter_by(status='waiting').order_by(
                Queue.priority_score.desc(),
                Queue.created_at.asc()
            ).all()
            
            # Calculate new positions
            new_positions = {}
            position_changes = []
            
            for idx, queue_entry in enumerate(waiting_entries, 1):
                old_position = self.position_cache.get(queue_entry.id)
                new_position = idx
                new_positions[queue_entry.id] = new_position
                
                # Track position changes
                if old_position != new_position:
                    position_changes.append({
                        'entry_id': queue_entry.id,
                        'customer_name': queue_entry.customer_name,
                        'service_type': queue_entry.service_type,
                        'old_position': old_position,
                        'new_position': new_position,
                        'priority_score': queue_entry.priority_score,
                        'estimated_wait_time': self._calculate_estimated_wait_time(new_position)
                    })
            
            # Remove entries no longer in waiting status from cache
            entries_to_remove = []
            for entry_id in self.position_cache:
                if entry_id not in new_positions:
                    entries_to_remove.append(entry_id)
            
            for entry_id in entries_to_remove:
                old_position = self.position_cache.pop(entry_id, None)
                if old_position:
                    # Find the entry details for removed entry
                    removed_entry = Queue.query.get(entry_id)
                    if removed_entry:
                        position_changes.append({
                            'entry_id': entry_id,
                            'customer_name': removed_entry.customer_name,
                            'service_type': removed_entry.service_type,
                            'old_position': old_position,
                            'new_position': None,
                            'priority_score': removed_entry.priority_score,
                            'status': removed_entry.status
                        })
            
            # Update cache
            self.position_cache = new_positions
            self.last_update = datetime.utcnow()
            self.update_count += 1
            
            # Broadcast updates if there are changes
            if position_changes:
                self._broadcast_position_updates(change_type, entry, position_changes, old_status)
            
        except Exception as e:
            logger.error(f"Error updating positions: {str(e)}")
    
    def _broadcast_position_updates(self, change_type: str, trigger_entry: Queue, 
                                  position_changes: List[Dict], old_status: Optional[str] = None):
        """Broadcast position updates via WebSocket"""
        try:
            # Prepare broadcast data
            broadcast_data = {
                'change_type': change_type,
                'trigger_entry': {
                    'id': trigger_entry.id,
                    'customer_name': trigger_entry.customer_name,
                    'service_type': trigger_entry.service_type,
                    'status': trigger_entry.status,
                    'priority_score': trigger_entry.priority_score
                },
                'position_changes': position_changes,
                'total_waiting': len([p for p in position_changes if p['new_position'] is not None]),
                'timestamp': self.last_update.isoformat(),
                'update_count': self.update_count
            }
            
            if old_status:
                broadcast_data['trigger_entry']['old_status'] = old_status
            
            # Emit general queue position update
            emit_queue_update(
                f"Queue positions updated: {len(position_changes)} changes",
                update_type='position_update',
                data=broadcast_data
            )
            
            # Emit individual position updates for affected customers
            for change in position_changes:
                socketio.emit('individual_position_update', {
                    'entry_id': change['entry_id'],
                    'customer_name': change['customer_name'],
                    'old_position': change['old_position'],
                    'new_position': change['new_position'],
                    'estimated_wait_time': change.get('estimated_wait_time'),
                    'timestamp': self.last_update.isoformat()
                }, room=f"customer_{change['entry_id']}")
            
            # Emit queue summary update
            socketio.emit('queue_summary_update', {
                'total_waiting': len([p for p in position_changes if p['new_position'] is not None]),
                'average_wait_time': self._calculate_average_wait_time(),
                'last_update': self.last_update.isoformat(),
                'update_type': change_type
            }, broadcast=True)
            
            logger.info(f"Broadcasted position updates: {len(position_changes)} changes")
            
        except Exception as e:
            logger.error(f"Error broadcasting position updates: {str(e)}")
    
    def _calculate_estimated_wait_time(self, position: int) -> int:
        """Calculate estimated wait time based on position"""
        try:
            # Base service time per customer (in minutes)
            base_service_time = self.config.AVERAGE_SERVICE_TIME if hasattr(self.config, 'AVERAGE_SERVICE_TIME') else 5
            
            # Get number of active agents
            from ..models import Agent
            active_agents = Agent.query.filter_by(status='available').count()
            active_agents = max(1, active_agents)  # Ensure at least 1
            
            # Calculate estimated wait time
            estimated_minutes = ((position - 1) * base_service_time) // active_agents
            return max(0, estimated_minutes)
            
        except Exception as e:
            logger.error(f"Error calculating wait time: {str(e)}")
            return position * 5  # Fallback: 5 minutes per position
    
    def _calculate_average_wait_time(self) -> float:
        """Calculate current average wait time"""
        try:
            total_positions = len(self.position_cache)
            if total_positions == 0:
                return 0.0
            
            total_wait_time = sum(
                self._calculate_estimated_wait_time(pos) 
                for pos in self.position_cache.values()
            )
            
            return total_wait_time / total_positions
            
        except Exception as e:
            logger.error(f"Error calculating average wait time: {str(e)}")
            return 0.0
    
    def get_current_positions(self) -> Dict[int, int]:
        """Get current position cache"""
        return self.position_cache.copy()
    
    def get_position_for_entry(self, entry_id: int) -> Optional[int]:
        """Get current position for a specific entry"""
        return self.position_cache.get(entry_id)
    
    def refresh_positions(self) -> Dict[str, Any]:
        """Manually refresh all positions (useful for initialization)"""
        try:
            logger.info("Manually refreshing queue positions")
            
            # Clear cache
            self.position_cache.clear()
            
            # Get all waiting entries
            waiting_entries = Queue.query.filter_by(status='waiting').order_by(
                Queue.priority_score.desc(),
                Queue.created_at.asc()
            ).all()
            
            # Rebuild position cache
            for idx, entry in enumerate(waiting_entries, 1):
                self.position_cache[entry.id] = idx
            
            self.last_update = datetime.utcnow()
            
            # Broadcast full refresh
            position_data = []
            for entry in waiting_entries:
                position_data.append({
                    'entry_id': entry.id,
                    'customer_name': entry.customer_name,
                    'service_type': entry.service_type,
                    'position': self.position_cache[entry.id],
                    'priority_score': entry.priority_score,
                    'estimated_wait_time': self._calculate_estimated_wait_time(self.position_cache[entry.id])
                })
            
            emit_queue_update(
                f"Queue positions refreshed: {len(waiting_entries)} entries",
                update_type='full_refresh',
                data={
                    'positions': position_data,
                    'total_waiting': len(waiting_entries),
                    'timestamp': self.last_update.isoformat()
                }
            )
            
            return {
                'success': True,
                'total_entries': len(waiting_entries),
                'positions': self.position_cache.copy(),
                'timestamp': self.last_update.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error refreshing positions: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get position tracker statistics"""
        return {
            'total_tracked_entries': len(self.position_cache),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'update_count': self.update_count,
            'average_wait_time': self._calculate_average_wait_time(),
            'positions': self.position_cache.copy()
        }

# Global position tracker instance
position_tracker = QueuePositionTracker()

def get_position_tracker() -> QueuePositionTracker:
    """Get the global position tracker instance"""
    return position_tracker

def refresh_queue_positions() -> Dict[str, Any]:
    """Refresh all queue positions"""
    return position_tracker.refresh_positions()

def get_queue_position(entry_id: int) -> Optional[int]:
    """Get position for a specific queue entry"""
    return position_tracker.get_position_for_entry(entry_id)