import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps
from flask import current_app
from ..extensions import socketio
from ..queue_logic.queue_config import get_queue_config

logger = logging.getLogger(__name__)

class WebSocketEmissionError(Exception):
    """Custom exception for WebSocket emission errors"""
    pass

class ReliableWebSocketEmitter:
    """Enhanced WebSocket emitter with retry mechanisms and error handling"""
    
    def __init__(self):
        self.config = get_queue_config()
        self.emission_stats = {
            'total_emissions': 0,
            'successful_emissions': 0,
            'failed_emissions': 0,
            'retry_attempts': 0
        }
    
    def emit_with_retry(self, event: str, data: Dict[str, Any], 
                       room: Optional[str] = None, 
                       broadcast: bool = True,
                       callback: Optional[Callable] = None) -> bool:
        """Emit WebSocket event with retry mechanism"""
        self.emission_stats['total_emissions'] += 1
        
        for attempt in range(self.config.WEBSOCKET_RETRY_ATTEMPTS):
            try:
                # Add metadata to the payload
                enhanced_data = self._enhance_payload(data)
                
                # Emit the event
                if room:
                    socketio.emit(event, enhanced_data, room=room, timeout=self.config.WEBSOCKET_TIMEOUT)
                else:
                    socketio.emit(event, enhanced_data, broadcast=broadcast, timeout=self.config.WEBSOCKET_TIMEOUT)
                
                # Log successful emission
                logger.debug(f"WebSocket event '{event}' emitted successfully on attempt {attempt + 1}")
                self.emission_stats['successful_emissions'] += 1
                
                # Execute callback if provided
                if callback:
                    callback(True, enhanced_data)
                
                return True
                
            except Exception as e:
                self.emission_stats['retry_attempts'] += 1
                logger.warning(f"WebSocket emission attempt {attempt + 1} failed for event '{event}': {str(e)}")
                
                # If this is the last attempt, log as error
                if attempt == self.config.WEBSOCKET_RETRY_ATTEMPTS - 1:
                    logger.error(f"All WebSocket emission attempts failed for event '{event}': {str(e)}")
                    self.emission_stats['failed_emissions'] += 1
                    
                    # Execute callback with failure status
                    if callback:
                        callback(False, data)
                    
                    return False
                
                # Wait before retry
                time.sleep(self.config.WEBSOCKET_RETRY_DELAY * (attempt + 1))
        
        return False
    
    def _enhance_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance payload with metadata"""
        enhanced_data = data.copy()
        enhanced_data.update({
            'timestamp': datetime.utcnow().isoformat(),
            'emission_id': f"{int(time.time() * 1000)}_{self.emission_stats['total_emissions']}",
            'server_time': datetime.utcnow().strftime('%H:%M:%S')
        })
        return enhanced_data
    
    def get_emission_stats(self) -> Dict[str, Any]:
        """Get emission statistics"""
        total = self.emission_stats['total_emissions']
        success_rate = (self.emission_stats['successful_emissions'] / total * 100) if total > 0 else 0
        
        return {
            **self.emission_stats,
            'success_rate': round(success_rate, 2),
            'failure_rate': round(100 - success_rate, 2)
        }
    
    def reset_stats(self) -> None:
        """Reset emission statistics"""
        self.emission_stats = {
            'total_emissions': 0,
            'successful_emissions': 0,
            'failed_emissions': 0,
            'retry_attempts': 0
        }

# Global emitter instance
reliable_emitter = ReliableWebSocketEmitter()

def emit_queue_update(message: str, update_type: str = 'general', 
                     data: Optional[Dict[str, Any]] = None,
                     room: Optional[str] = None) -> bool:
    """Enhanced queue update emission with retry mechanism"""
    try:
        payload = {
            'message': message,
            'type': update_type
        }
        
        if data:
            payload.update(data)
        
        def log_callback(success: bool, payload_data: Dict[str, Any]):
            if success:
                logger.info(f"Queue update emitted successfully: {update_type} - {message}")
            else:
                logger.error(f"Failed to emit queue update: {update_type} - {message}")
        
        return reliable_emitter.emit_with_retry(
            'queue_updated', 
            payload, 
            room=room,
            callback=log_callback
        )
        
    except Exception as e:
        logger.error(f"Error in emit_queue_update: {str(e)}")
        return False

def emit_agent_status_update(agent_id: int, status: str, 
                           metrics: Optional[Dict[str, Any]] = None,
                           room: Optional[str] = None) -> bool:
    """Enhanced agent status update emission with retry mechanism"""
    try:
        payload = {
            'agent_id': agent_id,
            'status': status
        }
        
        if metrics:
            payload['metrics'] = metrics
        
        def log_callback(success: bool, payload_data: Dict[str, Any]):
            if success:
                logger.info(f"Agent status update emitted successfully: Agent {agent_id} - {status}")
            else:
                logger.error(f"Failed to emit agent status update: Agent {agent_id} - {status}")
        
        return reliable_emitter.emit_with_retry(
            'agent_status_updated', 
            payload, 
            room=room,
            callback=log_callback
        )
        
    except Exception as e:
        logger.error(f"Error in emit_agent_status_update: {str(e)}")
        return False

def emit_metrics_update(metrics_data: Optional[Dict[str, Any]] = None,
                       room: Optional[str] = None) -> bool:
    """Enhanced metrics update emission with retry mechanism"""
    try:
        payload = {
            'metrics': metrics_data or {},
            'update_type': 'metrics'
        }
        
        def log_callback(success: bool, payload_data: Dict[str, Any]):
            if success:
                logger.info("Metrics update emitted successfully")
            else:
                logger.error("Failed to emit metrics update")
        
        return reliable_emitter.emit_with_retry(
            'metrics_updated', 
            payload, 
            room=room,
            callback=log_callback
        )
        
    except Exception as e:
        logger.error(f"Error in emit_metrics_update: {str(e)}")
        return False

def emit_queue_position_update(citizen_id: int, new_position: int, 
                              estimated_wait_time: int,
                              room: Optional[str] = None) -> bool:
    """Emit queue position update for specific citizen"""
    try:
        payload = {
            'citizen_id': citizen_id,
            'new_position': new_position,
            'estimated_wait_time': estimated_wait_time,
            'update_type': 'position_change'
        }
        
        def log_callback(success: bool, payload_data: Dict[str, Any]):
            if success:
                logger.debug(f"Queue position update emitted for citizen {citizen_id}: position {new_position}")
            else:
                logger.error(f"Failed to emit queue position update for citizen {citizen_id}")
        
        return reliable_emitter.emit_with_retry(
            'queue_position_updated', 
            payload, 
            room=room,
            callback=log_callback
        )
        
    except Exception as e:
        logger.error(f"Error in emit_queue_position_update: {str(e)}")
        return False

def get_websocket_stats() -> Dict[str, Any]:
    """Get WebSocket emission statistics"""
    return reliable_emitter.get_emission_stats()

def reset_websocket_stats() -> None:
    """Reset WebSocket emission statistics"""
    reliable_emitter.reset_stats()

def websocket_error_handler(f):
    """Decorator for handling WebSocket errors in routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"WebSocket error in {f.__name__}: {str(e)}")
            # Attempt to emit error notification
            emit_queue_update(
                f"System error occurred: {str(e)}",
                update_type='error',
                data={'error_source': f.__name__}
            )
            raise
    return decorated_function