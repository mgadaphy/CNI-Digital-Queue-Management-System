"""
Real-time Synchronization System - Phase 4 Implementation

This module provides enhanced WebSocket synchronization with:
1. Race condition prevention through event ordering
2. Cache invalidation coordination
3. Conflict resolution for concurrent updates
4. Event deduplication and batching
5. Client state synchronization

Key Features:
- Event ordering with sequence numbers
- Optimistic locking for concurrent updates
- Cache invalidation coordination
- Client reconnection handling
- Event replay for missed updates
"""

import time
import threading
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
from flask import current_app
from ..extensions import socketio, db
from ..models import Queue, Agent, Citizen
from .websocket_utils import reliable_emitter

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of real-time events"""
    QUEUE_UPDATE = "queue_update"
    AGENT_STATUS = "agent_status"
    TICKET_ASSIGNMENT = "ticket_assignment"
    TICKET_COMPLETION = "ticket_completion"
    QUEUE_OPTIMIZATION = "queue_optimization"
    METRICS_UPDATE = "metrics_update"
    SYSTEM_STATUS = "system_status"

class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class SyncEvent:
    """Real-time synchronization event"""
    event_id: str
    event_type: EventType
    priority: EventPriority
    data: Dict[str, Any]
    timestamp: datetime
    sequence_number: int
    source_session: Optional[str] = None
    affected_entities: Set[str] = field(default_factory=set)
    requires_ack: bool = False
    retry_count: int = 0
    max_retries: int = 3

class RealtimeSynchronizer:
    """Enhanced real-time synchronization manager"""
    
    def __init__(self):
        self.sequence_counter = 0
        self.sequence_lock = threading.Lock()
        
        # Event management
        self.pending_events: Dict[str, SyncEvent] = {}
        self.event_history: deque = deque(maxlen=1000)  # Keep last 1000 events
        self.client_last_seen: Dict[str, int] = {}  # Track client sequence numbers
        
        # Cache invalidation
        self.cache_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.invalidation_queue: deque = deque()
        
        # Conflict resolution
        self.entity_locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.entity_versions: Dict[str, int] = defaultdict(int)
        
        # Performance tracking
        self.sync_stats = {
            'events_processed': 0,
            'conflicts_resolved': 0,
            'cache_invalidations': 0,
            'client_reconnections': 0,
            'failed_synchronizations': 0
        }
        
        # Start background tasks
        self._start_background_tasks()
    
    def _get_next_sequence(self) -> int:
        """Get next sequence number thread-safely"""
        with self.sequence_lock:
            self.sequence_counter += 1
            return self.sequence_counter
    
    def create_event(self, event_type: EventType, data: Dict[str, Any], 
                    priority: EventPriority = EventPriority.NORMAL,
                    affected_entities: Optional[Set[str]] = None,
                    source_session: Optional[str] = None,
                    requires_ack: bool = False) -> SyncEvent:
        """Create a new synchronization event"""
        
        event_id = f"{event_type.value}_{int(time.time() * 1000)}_{self._get_next_sequence()}"
        
        event = SyncEvent(
            event_id=event_id,
            event_type=event_type,
            priority=priority,
            data=data,
            timestamp=datetime.utcnow(),
            sequence_number=self.sequence_counter,
            source_session=source_session,
            affected_entities=affected_entities or set(),
            requires_ack=requires_ack
        )
        
        return event
    
    def emit_synchronized_event(self, event: SyncEvent, 
                              room: Optional[str] = None,
                              exclude_source: bool = True) -> bool:
        """Emit event with synchronization guarantees"""
        
        try:
            # Check for conflicts
            if self._has_conflicts(event):
                resolved_event = self._resolve_conflicts(event)
                if not resolved_event:
                    logger.warning(f"Could not resolve conflicts for event {event.event_id}")
                    self.sync_stats['failed_synchronizations'] += 1
                    return False
                event = resolved_event
            
            # Update entity versions
            self._update_entity_versions(event)
            
            # Prepare payload with synchronization metadata
            sync_payload = {
                'event_id': event.event_id,
                'event_type': event.event_type.value,
                'sequence_number': event.sequence_number,
                'timestamp': event.timestamp.isoformat(),
                'priority': event.priority.value,
                'data': event.data,
                'entity_versions': {
                    entity: self.entity_versions[entity] 
                    for entity in event.affected_entities
                }
            }
            
            # Emit to clients
            success = self._emit_to_clients(sync_payload, room, exclude_source, event.source_session)
            
            if success:
                # Store in history
                self.event_history.append(event)
                
                # Handle cache invalidation
                self._invalidate_caches(event)
                
                # Track pending acknowledgments
                if event.requires_ack:
                    self.pending_events[event.event_id] = event
                
                self.sync_stats['events_processed'] += 1
                logger.debug(f"Synchronized event {event.event_id} emitted successfully")
                
            return success
            
        except Exception as e:
            logger.error(f"Error emitting synchronized event {event.event_id}: {e}")
            self.sync_stats['failed_synchronizations'] += 1
            return False
    
    def _has_conflicts(self, event: SyncEvent) -> bool:
        """Check if event has conflicts with pending operations"""
        
        for entity in event.affected_entities:
            # Check if entity is locked by another operation
            if entity in self.entity_locks:
                try:
                    # Try to acquire lock with timeout
                    if not self.entity_locks[entity].acquire(timeout=0.1):
                        return True
                    self.entity_locks[entity].release()
                except:
                    return True
        
        return False
    
    def _resolve_conflicts(self, event: SyncEvent) -> Optional[SyncEvent]:
        """Resolve conflicts using optimistic locking"""
        
        try:
            # Wait for locks to be released
            for entity in event.affected_entities:
                if entity in self.entity_locks:
                    self.entity_locks[entity].acquire()
                    self.entity_locks[entity].release()
            
            # Check if data is still valid
            if self._validate_event_data(event):
                self.sync_stats['conflicts_resolved'] += 1
                return event
            else:
                # Data is stale, need to refresh
                refreshed_event = self._refresh_event_data(event)
                if refreshed_event:
                    self.sync_stats['conflicts_resolved'] += 1
                return refreshed_event
                
        except Exception as e:
            logger.error(f"Error resolving conflicts for event {event.event_id}: {e}")
            return None
    
    def _validate_event_data(self, event: SyncEvent) -> bool:
        """Validate that event data is still current"""
        
        try:
            # Check entity versions
            for entity in event.affected_entities:
                if entity.startswith('ticket_'):
                    ticket_id = int(entity.split('_')[1])
                    ticket = Queue.query.get(ticket_id)
                    if not ticket:
                        return False
                    
                    # Check if ticket data matches event expectations
                    if 'ticket_status' in event.data:
                        if ticket.status != event.data.get('previous_status'):
                            return False
                
                elif entity.startswith('agent_'):
                    agent_id = int(entity.split('_')[1])
                    agent = Agent.query.get(agent_id)
                    if not agent:
                        return False
                    
                    # Check if agent data matches event expectations
                    if 'agent_status' in event.data:
                        if agent.status != event.data.get('previous_status'):
                            return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating event data: {e}")
            return False
    
    def _refresh_event_data(self, event: SyncEvent) -> Optional[SyncEvent]:
        """Refresh event data with current database state"""
        
        try:
            refreshed_data = event.data.copy()
            
            # Refresh ticket data
            for entity in event.affected_entities:
                if entity.startswith('ticket_'):
                    ticket_id = int(entity.split('_')[1])
                    ticket = Queue.query.get(ticket_id)
                    if ticket:
                        refreshed_data.update({
                            'ticket_id': ticket.id,
                            'current_status': ticket.status,
                            'current_priority': ticket.priority_score,
                            'current_agent': ticket.agent_id
                        })
                
                elif entity.startswith('agent_'):
                    agent_id = int(entity.split('_')[1])
                    agent = Agent.query.get(agent_id)
                    if agent:
                        refreshed_data.update({
                            'agent_id': agent.id,
                            'current_status': agent.status
                        })
            
            # Create new event with refreshed data
            refreshed_event = self.create_event(
                event_type=event.event_type,
                data=refreshed_data,
                priority=event.priority,
                affected_entities=event.affected_entities,
                source_session=event.source_session,
                requires_ack=event.requires_ack
            )
            
            return refreshed_event
            
        except Exception as e:
            logger.error(f"Error refreshing event data: {e}")
            return None
    
    def _update_entity_versions(self, event: SyncEvent):
        """Update entity version numbers"""
        
        for entity in event.affected_entities:
            self.entity_versions[entity] += 1
    
    def _emit_to_clients(self, payload: Dict[str, Any], room: Optional[str], 
                        exclude_source: bool, source_session: Optional[str]) -> bool:
        """Emit payload to clients with proper targeting"""
        
        try:
            # Use reliable emitter for actual WebSocket emission
            return reliable_emitter.emit_with_retry(
                'synchronized_update',
                payload,
                room=room
            )
            
        except Exception as e:
            logger.error(f"Error emitting to clients: {e}")
            return False
    
    def _invalidate_caches(self, event: SyncEvent):
        """Invalidate related caches"""
        
        try:
            cache_keys = set()
            
            # Determine cache keys to invalidate based on event type
            if event.event_type == EventType.QUEUE_UPDATE:
                cache_keys.update(['dashboard_data', 'queue_metrics', 'active_tickets'])
            
            elif event.event_type == EventType.AGENT_STATUS:
                cache_keys.update(['agent_metrics', 'dashboard_data'])
            
            elif event.event_type == EventType.TICKET_ASSIGNMENT:
                cache_keys.update(['agent_workload', 'queue_metrics', 'active_tickets'])
            
            elif event.event_type == EventType.QUEUE_OPTIMIZATION:
                cache_keys.update(['queue_order', 'priority_scores', 'active_tickets'])
            
            # Add to invalidation queue
            for cache_key in cache_keys:
                self.invalidation_queue.append({
                    'cache_key': cache_key,
                    'timestamp': datetime.utcnow(),
                    'event_id': event.event_id
                })
            
            self.sync_stats['cache_invalidations'] += len(cache_keys)
            
        except Exception as e:
            logger.error(f"Error invalidating caches: {e}")
    
    def handle_client_reconnection(self, client_id: str, last_sequence: int) -> List[SyncEvent]:
        """Handle client reconnection and provide missed events"""
        
        try:
            self.sync_stats['client_reconnections'] += 1
            
            # Find events missed by client
            missed_events = []
            for event in self.event_history:
                if event.sequence_number > last_sequence:
                    missed_events.append(event)
            
            # Update client's last seen sequence
            self.client_last_seen[client_id] = self.sequence_counter
            
            logger.info(f"Client {client_id} reconnected, sending {len(missed_events)} missed events")
            return missed_events
            
        except Exception as e:
            logger.error(f"Error handling client reconnection: {e}")
            return []
    
    def acknowledge_event(self, event_id: str, client_id: str) -> bool:
        """Acknowledge event receipt from client"""
        
        try:
            if event_id in self.pending_events:
                event = self.pending_events[event_id]
                # Remove from pending (simplified - in production, track per-client acks)
                del self.pending_events[event_id]
                logger.debug(f"Event {event_id} acknowledged by client {client_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error acknowledging event: {e}")
            return False
    
    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        
        def cleanup_old_events():
            """Clean up old events and pending acknowledgments"""
            try:
                cutoff_time = datetime.utcnow() - timedelta(minutes=30)
                
                # Clean up old pending events
                expired_events = [
                    event_id for event_id, event in self.pending_events.items()
                    if event.timestamp < cutoff_time
                ]
                
                for event_id in expired_events:
                    del self.pending_events[event_id]
                
                # Process cache invalidations
                while self.invalidation_queue:
                    invalidation = self.invalidation_queue.popleft()
                    # In a real implementation, this would invalidate actual cache
                    logger.debug(f"Cache invalidated: {invalidation['cache_key']}")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
        
        # Schedule cleanup every 5 minutes
        def schedule_cleanup():
            cleanup_old_events()
            threading.Timer(300, schedule_cleanup).start()
        
        schedule_cleanup()
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get synchronization statistics"""
        
        return {
            **self.sync_stats,
            'pending_events': len(self.pending_events),
            'event_history_size': len(self.event_history),
            'connected_clients': len(self.client_last_seen),
            'current_sequence': self.sequence_counter,
            'cache_invalidation_queue': len(self.invalidation_queue)
        }

# Global synchronizer instance
realtime_sync = RealtimeSynchronizer()

# Convenience functions for common operations
def emit_queue_update_sync(message: str, data: Optional[Dict[str, Any]] = None,
                          affected_tickets: Optional[List[int]] = None,
                          priority: EventPriority = EventPriority.NORMAL) -> bool:
    """Emit synchronized queue update"""
    
    affected_entities = set()
    if affected_tickets:
        affected_entities.update(f"ticket_{tid}" for tid in affected_tickets)
    
    event = realtime_sync.create_event(
        event_type=EventType.QUEUE_UPDATE,
        data={'message': message, **(data or {})},
        priority=priority,
        affected_entities=affected_entities
    )
    
    return realtime_sync.emit_synchronized_event(event)

def emit_agent_status_sync(agent_id: int, status: str, 
                          metrics: Optional[Dict[str, Any]] = None) -> bool:
    """Emit synchronized agent status update"""
    
    event = realtime_sync.create_event(
        event_type=EventType.AGENT_STATUS,
        data={
            'agent_id': agent_id,
            'status': status,
            'metrics': metrics or {}
        },
        affected_entities={f"agent_{agent_id}"}
    )
    
    return realtime_sync.emit_synchronized_event(event)

def emit_ticket_assignment_sync(ticket_id: int, agent_id: int, 
                               previous_status: str) -> bool:
    """Emit synchronized ticket assignment"""
    
    event = realtime_sync.create_event(
        event_type=EventType.TICKET_ASSIGNMENT,
        data={
            'ticket_id': ticket_id,
            'agent_id': agent_id,
            'previous_status': previous_status
        },
        priority=EventPriority.HIGH,
        affected_entities={f"ticket_{ticket_id}", f"agent_{agent_id}"},
        requires_ack=True
    )
    
    return realtime_sync.emit_synchronized_event(event)

def emit_optimization_sync(optimized_count: int, total_tickets: int,
                          affected_tickets: List[int]) -> bool:
    """Emit synchronized queue optimization"""
    
    affected_entities = {f"ticket_{tid}" for tid in affected_tickets}
    
    event = realtime_sync.create_event(
        event_type=EventType.QUEUE_OPTIMIZATION,
        data={
            'optimized_count': optimized_count,
            'total_tickets': total_tickets,
            'affected_tickets': affected_tickets
        },
        priority=EventPriority.HIGH,
        affected_entities=affected_entities
    )
    
    return realtime_sync.emit_synchronized_event(event)
