from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..utils.config_manager import get_config_manager, get_queue_optimization_config
from ..utils.queue_logger import get_queue_logger
from dataclasses import asdict
import json

config_api_bp = Blueprint('config_api', __name__)

@config_api_bp.route('/current', methods=['GET'])
@jwt_required()
def get_current_config():
    """Get current queue optimization configuration"""
    try:
        config = get_queue_optimization_config()
        config_dict = asdict(config)
        
        return jsonify({
            'success': True,
            'configuration': config_dict
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_current_config'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving configuration: {str(e)}'
        }), 500

@config_api_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_config_categories():
    """Get all configuration categories"""
    try:
        config_manager = get_config_manager()
        categories = config_manager.get_all_categories()
        
        return jsonify({
            'success': True,
            'categories': categories
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_config_categories'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving categories: {str(e)}'
        }), 500

@config_api_bp.route('/category/<category>', methods=['GET'])
@jwt_required()
def get_config_by_category(category):
    """Get configuration settings by category"""
    try:
        config_manager = get_config_manager()
        config_data = config_manager.get_config_by_category(category)
        
        return jsonify({
            'success': True,
            'category': category,
            'configuration': config_data
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {
            'endpoint': 'get_config_by_category',
            'category': category
        })
        return jsonify({
            'success': False,
            'message': f'Error retrieving configuration for category {category}: {str(e)}'
        }), 500

@config_api_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_config():
    """Update configuration settings"""
    try:
        data = request.get_json()
        
        if not data or 'updates' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing updates in request body'
            }), 400
        
        updates = data['updates']
        user_id = get_jwt_identity()
        
        # Validate that updates is a dictionary
        if not isinstance(updates, dict):
            return jsonify({
                'success': False,
                'message': 'Updates must be a dictionary of key-value pairs'
            }), 400
        
        config_manager = get_config_manager()
        success = config_manager.update_config(updates, updated_by=str(user_id))
        
        if success:
            # Log configuration change
            queue_logger = get_queue_logger()
            queue_logger.log_queue_event('configuration_updated', {
                'updated_keys': list(updates.keys()),
                'updated_by': user_id,
                'updates': updates
            })
            
            # Get updated configuration
            updated_config = get_queue_optimization_config()
            
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully',
                'updated_configuration': asdict(updated_config)
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update configuration. Check validation errors.'
            }), 400
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {
            'endpoint': 'update_config',
            'user_id': get_jwt_identity()
        })
        return jsonify({
            'success': False,
            'message': f'Error updating configuration: {str(e)}'
        }), 500

@config_api_bp.route('/validate', methods=['POST'])
@jwt_required()
def validate_config():
    """Validate configuration settings without applying them"""
    try:
        data = request.get_json()
        
        if not data or 'configuration' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing configuration in request body'
            }), 400
        
        config_data = data['configuration']
        
        # Import the configuration class
        from ..utils.config_manager import QueueOptimizationConfig
        
        try:
            # Create configuration object for validation
            config = QueueOptimizationConfig(**config_data)
            validation_errors = config.validate()
            
            if validation_errors:
                return jsonify({
                    'success': False,
                    'valid': False,
                    'errors': validation_errors
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'valid': True,
                    'message': 'Configuration is valid'
                }), 200
                
        except TypeError as e:
            return jsonify({
                'success': False,
                'valid': False,
                'errors': [f'Invalid configuration structure: {str(e)}']
            }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'validate_config'})
        return jsonify({
            'success': False,
            'message': f'Error validating configuration: {str(e)}'
        }), 500

@config_api_bp.route('/reset', methods=['POST'])
@jwt_required()
def reset_config():
    """Reset configuration to defaults"""
    try:
        data = request.get_json() or {}
        category = data.get('category')  # Optional: reset specific category
        user_id = get_jwt_identity()
        
        config_manager = get_config_manager()
        success = config_manager.reset_to_defaults(category)
        
        if success:
            # Log configuration reset
            queue_logger = get_queue_logger()
            queue_logger.log_queue_event('configuration_reset', {
                'category': category or 'all',
                'reset_by': user_id
            })
            
            # Get reset configuration
            reset_config = get_queue_optimization_config()
            
            return jsonify({
                'success': True,
                'message': f'Configuration reset to defaults for {category or "all categories"}',
                'configuration': asdict(reset_config)
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to reset configuration'
            }), 500
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {
            'endpoint': 'reset_config',
            'user_id': get_jwt_identity()
        })
        return jsonify({
            'success': False,
            'message': f'Error resetting configuration: {str(e)}'
        }), 500

@config_api_bp.route('/schema', methods=['GET'])
@jwt_required()
def get_config_schema():
    """Get configuration schema for frontend validation"""
    try:
        from ..utils.config_manager import QueueOptimizationConfig
        import inspect
        
        # Get field information from dataclass
        fields = QueueOptimizationConfig.__dataclass_fields__
        
        schema = {
            'fields': {},
            'categories': {
                'general': ['optimization_interval_minutes', 'optimization_batch_size', 'max_optimization_time_seconds'],
                'priority_weights': ['wait_time_weight', 'service_complexity_weight', 'citizen_priority_weight', 'demographic_weight'],
                'thresholds': ['high_priority_threshold', 'reoptimization_threshold', 'max_wait_time_minutes'],
                'service_settings': ['average_service_time_minutes', 'service_time_buffer_percentage'],
                'agent_settings': ['enable_intelligent_assignment', 'agent_specialization_weight', 'agent_workload_balance_weight'],
                'performance': ['enable_performance_monitoring', 'performance_log_level', 'cache_optimization_results', 'cache_ttl_seconds'],
                'database': ['enable_transaction_optimization', 'transaction_retry_attempts', 'transaction_timeout_seconds'],
                'notifications': ['enable_position_notifications', 'notification_threshold_positions', 'websocket_broadcast_enabled']
            },
            'validation_rules': {
                'optimization_interval_minutes': {'min': 1, 'max': 60, 'type': 'int'},
                'optimization_batch_size': {'min': 10, 'max': 1000, 'type': 'int'},
                'max_optimization_time_seconds': {'min': 5, 'max': 300, 'type': 'int'},
                'wait_time_weight': {'min': 0.0, 'max': 1.0, 'type': 'float'},
                'service_complexity_weight': {'min': 0.0, 'max': 1.0, 'type': 'float'},
                'citizen_priority_weight': {'min': 0.0, 'max': 1.0, 'type': 'float'},
                'demographic_weight': {'min': 0.0, 'max': 1.0, 'type': 'float'},
                'high_priority_threshold': {'min': 0.0, 'max': 100.0, 'type': 'float'},
                'reoptimization_threshold': {'min': 0.0, 'max': 100.0, 'type': 'float'},
                'max_wait_time_minutes': {'min': 1, 'max': 480, 'type': 'int'},
                'average_service_time_minutes': {'min': 1, 'max': 60, 'type': 'int'},
                'service_time_buffer_percentage': {'min': 0.0, 'max': 100.0, 'type': 'float'},
                'performance_log_level': {'options': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 'type': 'str'}
            }
        }
        
        # Add field information
        for field_name, field_info in fields.items():
            field_type = field_info.type
            default_value = field_info.default
            
            schema['fields'][field_name] = {
                'type': field_type.__name__ if hasattr(field_type, '__name__') else str(field_type),
                'default': default_value,
                'required': field_info.default == field_info.default_factory if hasattr(field_info, 'default_factory') else True
            }
        
        return jsonify({
            'success': True,
            'schema': schema
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_config_schema'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving configuration schema: {str(e)}'
        }), 500

@config_api_bp.route('/history', methods=['GET'])
@jwt_required()
def get_config_history():
    """Get configuration change history"""
    try:
        from ..utils.config_manager import ConfigurationSetting
        from sqlalchemy import desc
        
        limit = request.args.get('limit', 50, type=int)
        
        # Get recent configuration changes
        recent_changes = ConfigurationSetting.query.order_by(
            desc(ConfigurationSetting.updated_at)
        ).limit(limit).all()
        
        history = []
        for change in recent_changes:
            history.append({
                'key': change.key,
                'value': change.value,
                'category': change.category,
                'updated_at': change.updated_at.isoformat(),
                'updated_by': change.updated_by,
                'description': change.description
            })
        
        return jsonify({
            'success': True,
            'history': history,
            'total_entries': len(history)
        }), 200
        
    except Exception as e:
        queue_logger = get_queue_logger()
        queue_logger.log_error(e, {'endpoint': 'get_config_history'})
        return jsonify({
            'success': False,
            'message': f'Error retrieving configuration history: {str(e)}'
        }), 500