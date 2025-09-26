import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from flask import current_app
from ..extensions import db
from ..models import db as database
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
import logging

logger = logging.getLogger(__name__)

# Configuration model for database storage
class ConfigurationSetting(db.Model):
    __tablename__ = 'configuration_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    data_type = Column(String(50), nullable=False)  # 'int', 'float', 'bool', 'str', 'json'
    category = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100))
    
    def __repr__(self):
        return f'<ConfigurationSetting {self.key}={self.value}>'

@dataclass
class QueueOptimizationConfig:
    """Queue optimization configuration with validation"""
    
    # Scheduling settings
    optimization_interval_minutes: int = 5
    optimization_batch_size: int = 50
    max_optimization_time_seconds: int = 30
    
    # Priority calculation weights
    wait_time_weight: float = 0.4
    service_complexity_weight: float = 0.3
    citizen_priority_weight: float = 0.2
    demographic_weight: float = 0.1
    
    # Thresholds
    high_priority_threshold: float = 80.0
    reoptimization_threshold: float = 70.0
    max_wait_time_minutes: int = 120
    
    # Service time settings
    average_service_time_minutes: int = 5
    service_time_buffer_percentage: float = 20.0
    
    # Agent assignment settings
    enable_intelligent_assignment: bool = True
    agent_specialization_weight: float = 0.3
    agent_workload_balance_weight: float = 0.7
    
    # Performance settings
    enable_performance_monitoring: bool = True
    performance_log_level: str = 'INFO'
    cache_optimization_results: bool = True
    cache_ttl_seconds: int = 300
    
    # Database settings
    enable_transaction_optimization: bool = True
    transaction_retry_attempts: int = 3
    transaction_timeout_seconds: int = 10
    
    # Notification settings
    enable_position_notifications: bool = True
    notification_threshold_positions: int = 3
    websocket_broadcast_enabled: bool = True
    
    def validate(self) -> List[str]:
        """Validate configuration values"""
        errors = []
        
        # Validate ranges
        if not (1 <= self.optimization_interval_minutes <= 60):
            errors.append("optimization_interval_minutes must be between 1 and 60")
        
        if not (10 <= self.optimization_batch_size <= 1000):
            errors.append("optimization_batch_size must be between 10 and 1000")
        
        if not (5 <= self.max_optimization_time_seconds <= 300):
            errors.append("max_optimization_time_seconds must be between 5 and 300")
        
        # Validate weights sum to approximately 1.0
        total_weight = (self.wait_time_weight + self.service_complexity_weight + 
                       self.citizen_priority_weight + self.demographic_weight)
        if not (0.95 <= total_weight <= 1.05):
            errors.append(f"Priority weights must sum to approximately 1.0, got {total_weight}")
        
        # Validate individual weights
        weights = [
            ('wait_time_weight', self.wait_time_weight),
            ('service_complexity_weight', self.service_complexity_weight),
            ('citizen_priority_weight', self.citizen_priority_weight),
            ('demographic_weight', self.demographic_weight)
        ]
        
        for name, weight in weights:
            if not (0.0 <= weight <= 1.0):
                errors.append(f"{name} must be between 0.0 and 1.0")
        
        # Validate thresholds
        if not (0.0 <= self.high_priority_threshold <= 100.0):
            errors.append("high_priority_threshold must be between 0.0 and 100.0")
        
        if not (0.0 <= self.reoptimization_threshold <= 100.0):
            errors.append("reoptimization_threshold must be between 0.0 and 100.0")
        
        # Validate service time settings
        if not (1 <= self.average_service_time_minutes <= 60):
            errors.append("average_service_time_minutes must be between 1 and 60")
        
        if not (0.0 <= self.service_time_buffer_percentage <= 100.0):
            errors.append("service_time_buffer_percentage must be between 0.0 and 100.0")
        
        # Validate performance settings
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.performance_log_level not in valid_log_levels:
            errors.append(f"performance_log_level must be one of {valid_log_levels}")
        
        return errors

class ConfigurationManager:
    """Manages queue optimization configuration with database persistence"""
    
    def __init__(self, app=None):
        self.app = app
        self._config_cache = {}
        self._cache_timestamp = None
        self.cache_ttl = 300  # 5 minutes
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize configuration manager with Flask app"""
        self.app = app
        
        # Create configuration table if it doesn't exist
        with app.app_context():
            try:
                db.create_all()
                self._initialize_default_config()
            except Exception as e:
                logger.error(f"Failed to initialize configuration: {e}")
        
        # Store manager instance in app
        app.config_manager = self
    
    def _initialize_default_config(self):
        """Initialize default configuration in database"""
        default_config = QueueOptimizationConfig()
        
        # Convert dataclass to configuration entries
        config_dict = asdict(default_config)
        
        for key, value in config_dict.items():
            existing = ConfigurationSetting.query.filter_by(key=key).first()
            
            if not existing:
                # Determine data type
                if isinstance(value, bool):
                    data_type = 'bool'
                elif isinstance(value, int):
                    data_type = 'int'
                elif isinstance(value, float):
                    data_type = 'float'
                elif isinstance(value, str):
                    data_type = 'str'
                else:
                    data_type = 'json'
                    value = json.dumps(value)
                
                # Determine category
                if 'weight' in key:
                    category = 'priority_weights'
                elif 'threshold' in key:
                    category = 'thresholds'
                elif 'service' in key:
                    category = 'service_settings'
                elif 'agent' in key:
                    category = 'agent_settings'
                elif 'performance' in key or 'monitoring' in key:
                    category = 'performance'
                elif 'transaction' in key or 'database' in key:
                    category = 'database'
                elif 'notification' in key or 'websocket' in key:
                    category = 'notifications'
                else:
                    category = 'general'
                
                config_entry = ConfigurationSetting(
                    key=key,
                    value=str(value),
                    data_type=data_type,
                    category=category,
                    description=f"Default {key.replace('_', ' ')} setting",
                    updated_by='system'
                )
                
                db.session.add(config_entry)
        
        try:
            db.session.commit()
            logger.info("Default configuration initialized")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to initialize default configuration: {e}")
    
    def get_config(self, use_cache: bool = True) -> QueueOptimizationConfig:
        """Get current configuration"""
        if use_cache and self._is_cache_valid():
            return self._config_cache.get('config')
        
        try:
            # Load configuration from database
            config_entries = ConfigurationSetting.query.filter_by(is_active=True).all()
            
            config_dict = {}
            for entry in config_entries:
                value = self._parse_config_value(entry.value, entry.data_type)
                config_dict[entry.key] = value
            
            # Create configuration object
            config = QueueOptimizationConfig(**config_dict)
            
            # Validate configuration
            validation_errors = config.validate()
            if validation_errors:
                logger.warning(f"Configuration validation errors: {validation_errors}")
            
            # Update cache
            self._config_cache = {
                'config': config,
                'timestamp': datetime.utcnow()
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Return default configuration as fallback
            return QueueOptimizationConfig()
    
    def update_config(self, updates: Dict[str, Any], updated_by: str = 'system') -> bool:
        """Update configuration settings"""
        try:
            # Validate updates first
            current_config = self.get_config(use_cache=False)
            config_dict = asdict(current_config)
            config_dict.update(updates)
            
            # Create temporary config for validation
            temp_config = QueueOptimizationConfig(**config_dict)
            validation_errors = temp_config.validate()
            
            if validation_errors:
                logger.error(f"Configuration validation failed: {validation_errors}")
                return False
            
            # Apply updates to database
            for key, value in updates.items():
                config_entry = ConfigurationSetting.query.filter_by(key=key).first()
                
                if config_entry:
                    config_entry.value = str(value)
                    config_entry.updated_at = datetime.utcnow()
                    config_entry.updated_by = updated_by
                else:
                    # Create new configuration entry
                    data_type = self._determine_data_type(value)
                    config_entry = ConfigurationSetting(
                        key=key,
                        value=str(value),
                        data_type=data_type,
                        category='custom',
                        description=f"Custom {key} setting",
                        updated_by=updated_by
                    )
                    db.session.add(config_entry)
            
            db.session.commit()
            
            # Clear cache to force reload
            self._config_cache = {}
            
            logger.info(f"Configuration updated by {updated_by}: {list(updates.keys())}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update configuration: {e}")
            return False
    
    def get_config_by_category(self, category: str) -> Dict[str, Any]:
        """Get configuration settings by category"""
        try:
            config_entries = ConfigurationSetting.query.filter_by(
                category=category,
                is_active=True
            ).all()
            
            result = {}
            for entry in config_entries:
                value = self._parse_config_value(entry.value, entry.data_type)
                result[entry.key] = {
                    'value': value,
                    'description': entry.description,
                    'updated_at': entry.updated_at.isoformat(),
                    'updated_by': entry.updated_by
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get configuration by category {category}: {e}")
            return {}
    
    def get_all_categories(self) -> List[str]:
        """Get all configuration categories"""
        try:
            categories = db.session.query(ConfigurationSetting.category).distinct().all()
            return [cat[0] for cat in categories]
        except Exception as e:
            logger.error(f"Failed to get configuration categories: {e}")
            return []
    
    def reset_to_defaults(self, category: Optional[str] = None) -> bool:
        """Reset configuration to defaults"""
        try:
            if category:
                ConfigurationSetting.query.filter_by(category=category).delete()
            else:
                ConfigurationSetting.query.delete()
            
            db.session.commit()
            
            # Reinitialize defaults
            self._initialize_default_config()
            
            # Clear cache
            self._config_cache = {}
            
            logger.info(f"Configuration reset to defaults for category: {category or 'all'}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to reset configuration: {e}")
            return False
    
    def _is_cache_valid(self) -> bool:
        """Check if configuration cache is still valid"""
        if not self._config_cache or 'timestamp' not in self._config_cache:
            return False
        
        cache_age = (datetime.utcnow() - self._config_cache['timestamp']).total_seconds()
        return cache_age < self.cache_ttl
    
    def _parse_config_value(self, value: str, data_type: str) -> Any:
        """Parse configuration value based on data type"""
        try:
            if data_type == 'bool':
                return value.lower() in ('true', '1', 'yes', 'on')
            elif data_type == 'int':
                return int(value)
            elif data_type == 'float':
                return float(value)
            elif data_type == 'json':
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to parse config value '{value}' as {data_type}: {e}")
            return value
    
    def _determine_data_type(self, value: Any) -> str:
        """Determine data type for a configuration value"""
        if isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int'
        elif isinstance(value, float):
            return 'float'
        elif isinstance(value, (dict, list)):
            return 'json'
        else:
            return 'str'

# Global configuration manager instance
_config_manager = None

def get_config_manager(app=None) -> ConfigurationManager:
    """Get or create configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigurationManager(app)
    elif app is not None and _config_manager.app is None:
        _config_manager.init_app(app)
    
    return _config_manager

def get_queue_optimization_config() -> QueueOptimizationConfig:
    """Get current queue optimization configuration"""
    config_manager = get_config_manager()
    return config_manager.get_config()