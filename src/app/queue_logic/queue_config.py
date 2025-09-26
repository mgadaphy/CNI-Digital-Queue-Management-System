from typing import Dict, Any
import os
from dataclasses import dataclass

@dataclass
class QueueOptimizationConfig:
    """Configuration settings for queue optimization"""
    
    # Priority score update thresholds
    PRIORITY_UPDATE_THRESHOLD: float = float(os.environ.get('PRIORITY_UPDATE_THRESHOLD', '25.0'))
    SIGNIFICANT_PRIORITY_CHANGE: float = float(os.environ.get('SIGNIFICANT_PRIORITY_CHANGE', '100.0'))
    
    # Queue optimization intervals (in minutes)
    PERIODIC_OPTIMIZATION_INTERVAL: int = int(os.environ.get('PERIODIC_OPTIMIZATION_INTERVAL', '5'))
    REOPTIMIZATION_INTERVAL: int = int(os.environ.get('REOPTIMIZATION_INTERVAL', '15'))
    
    # WebSocket emission settings
    WEBSOCKET_RETRY_ATTEMPTS: int = int(os.environ.get('WEBSOCKET_RETRY_ATTEMPTS', '3'))
    WEBSOCKET_RETRY_DELAY: float = float(os.environ.get('WEBSOCKET_RETRY_DELAY', '1.0'))
    WEBSOCKET_TIMEOUT: float = float(os.environ.get('WEBSOCKET_TIMEOUT', '5.0'))
    
    # Database transaction settings
    DB_TRANSACTION_TIMEOUT: int = int(os.environ.get('DB_TRANSACTION_TIMEOUT', '30'))
    DB_RETRY_ATTEMPTS: int = int(os.environ.get('DB_RETRY_ATTEMPTS', '3'))
    
    # Queue position update settings
    QUEUE_POSITION_UPDATE_BATCH_SIZE: int = int(os.environ.get('QUEUE_POSITION_UPDATE_BATCH_SIZE', '50'))
    REAL_TIME_UPDATE_ENABLED: bool = os.environ.get('REAL_TIME_UPDATE_ENABLED', 'true').lower() == 'true'
    
    # Queue optimization settings
    OPTIMIZATION_BATCH_SIZE: int = int(os.environ.get('OPTIMIZATION_BATCH_SIZE', '100'))
    MAX_QUEUE_SIZE: int = int(os.environ.get('MAX_QUEUE_SIZE', '1000'))
    AVERAGE_SERVICE_TIME: int = int(os.environ.get('AVERAGE_SERVICE_TIME', '5'))
    
    # Performance monitoring
    PERFORMANCE_METRICS_ENABLED: bool = os.environ.get('PERFORMANCE_METRICS_ENABLED', 'true').lower() == 'true'
    METRICS_COLLECTION_INTERVAL: int = int(os.environ.get('METRICS_COLLECTION_INTERVAL', '60'))
    METRICS_RETENTION_DAYS: int = int(os.environ.get('METRICS_RETENTION_DAYS', '30'))
    
    # Advanced algorithm settings
    ADAPTIVE_PRIORITY_ENABLED: bool = os.environ.get('ADAPTIVE_PRIORITY_ENABLED', 'true').lower() == 'true'
    PREDICTIVE_SCHEDULING_ENABLED: bool = os.environ.get('PREDICTIVE_SCHEDULING_ENABLED', 'true').lower() == 'true'
    FAIRNESS_WEIGHTED_ENABLED: bool = os.environ.get('FAIRNESS_WEIGHTED_ENABLED', 'true').lower() == 'true'
    
    # Wait time thresholds
    LONG_WAIT_THRESHOLD_MINUTES: int = int(os.environ.get('LONG_WAIT_THRESHOLD_MINUTES', '30'))
    CRITICAL_WAIT_THRESHOLD_MINUTES: int = int(os.environ.get('CRITICAL_WAIT_THRESHOLD_MINUTES', '60'))
    
    # System load thresholds
    HIGH_LOAD_THRESHOLD: float = float(os.environ.get('HIGH_LOAD_THRESHOLD', '0.8'))
    CRITICAL_LOAD_THRESHOLD: float = float(os.environ.get('CRITICAL_LOAD_THRESHOLD', '0.95'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'priority_update_threshold': self.PRIORITY_UPDATE_THRESHOLD,
            'significant_priority_change': self.SIGNIFICANT_PRIORITY_CHANGE,
            'periodic_optimization_interval': self.PERIODIC_OPTIMIZATION_INTERVAL,
            'reoptimization_interval': self.REOPTIMIZATION_INTERVAL,
            'websocket_retry_attempts': self.WEBSOCKET_RETRY_ATTEMPTS,
            'websocket_retry_delay': self.WEBSOCKET_RETRY_DELAY,
            'websocket_timeout': self.WEBSOCKET_TIMEOUT,
            'db_transaction_timeout': self.DB_TRANSACTION_TIMEOUT,
            'db_retry_attempts': self.DB_RETRY_ATTEMPTS,
            'queue_position_update_batch_size': self.QUEUE_POSITION_UPDATE_BATCH_SIZE,
            'real_time_update_enabled': self.REAL_TIME_UPDATE_ENABLED,
            'performance_metrics_enabled': self.PERFORMANCE_METRICS_ENABLED,
            'metrics_collection_interval': self.METRICS_COLLECTION_INTERVAL,
            'adaptive_priority_enabled': self.ADAPTIVE_PRIORITY_ENABLED,
            'predictive_scheduling_enabled': self.PREDICTIVE_SCHEDULING_ENABLED,
            'fairness_weighted_enabled': self.FAIRNESS_WEIGHTED_ENABLED,
            'long_wait_threshold_minutes': self.LONG_WAIT_THRESHOLD_MINUTES,
            'critical_wait_threshold_minutes': self.CRITICAL_WAIT_THRESHOLD_MINUTES,
            'high_load_threshold': self.HIGH_LOAD_THRESHOLD,
            'critical_load_threshold': self.CRITICAL_LOAD_THRESHOLD
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'QueueOptimizationConfig':
        """Create configuration from dictionary"""
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key.upper()):
                setattr(config, key.upper(), value)
        return config

# Global configuration instance
queue_config = QueueOptimizationConfig()

def get_queue_config() -> QueueOptimizationConfig:
    """Get the global queue configuration instance"""
    return queue_config

def update_queue_config(new_config: Dict[str, Any]) -> None:
    """Update the global queue configuration"""
    global queue_config
    for key, value in new_config.items():
        if hasattr(queue_config, key.upper()):
            setattr(queue_config, key.upper(), value)

def reset_queue_config() -> None:
    """Reset configuration to default values"""
    global queue_config
    queue_config = QueueOptimizationConfig()