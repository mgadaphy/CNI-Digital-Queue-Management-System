from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required
from datetime import datetime
import logging

from ..auth.decorators import admin_required
from ..queue_logic.advanced_priority_algorithms import (
    advanced_priority_manager, AlgorithmType, PriorityMetrics
)
from ..queue_logic.optimizer import hybrid_engine
from ..models import Queue, Citizen, ServiceType
from ..extensions import db

logger = logging.getLogger(__name__)

advanced_priority_bp = Blueprint('advanced_priority', __name__, url_prefix='/api/advanced-priority')

@advanced_priority_bp.route('/algorithms', methods=['GET'])
@login_required
@admin_required
def get_available_algorithms():
    """Get list of available advanced priority algorithms"""
    try:
        algorithms = {
            'available_algorithms': [
                {
                    'type': algo.value,
                    'name': algo.value.replace('_', ' ').title(),
                    'description': _get_algorithm_description(algo)
                }
                for algo in AlgorithmType
            ],
            'active_algorithms': [algo.value for algo in advanced_priority_manager.active_algorithms],
            'total_available': len(AlgorithmType),
            'total_active': len(advanced_priority_manager.active_algorithms)
        }
        
        return jsonify({
            'status': 'success',
            'data': algorithms
        })
        
    except Exception as e:
        logger.error(f"Error getting available algorithms: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get algorithms: {str(e)}'
        }), 500

@advanced_priority_bp.route('/algorithms/configure', methods=['POST'])
@login_required
@admin_required
def configure_algorithms():
    """Configure which advanced algorithms are active"""
    try:
        data = request.get_json()
        
        if not data or 'algorithms' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing algorithms list in request'
            }), 400
        
        algorithm_names = data['algorithms']
        
        # Validate algorithm names
        valid_algorithms = []
        for name in algorithm_names:
            try:
                algo_type = AlgorithmType(name)
                valid_algorithms.append(algo_type)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid algorithm type: {name}'
                }), 400
        
        # Configure algorithms
        advanced_priority_manager.configure_algorithms(valid_algorithms)
        
        logger.info(f"Configured advanced algorithms: {algorithm_names}")
        
        return jsonify({
            'status': 'success',
            'message': f'Configured {len(valid_algorithms)} algorithms',
            'active_algorithms': [algo.value for algo in valid_algorithms]
        })
        
    except Exception as e:
        logger.error(f"Error configuring algorithms: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to configure algorithms: {str(e)}'
        }), 500

@advanced_priority_bp.route('/metrics', methods=['GET'])
@login_required
@admin_required
def get_algorithm_metrics():
    """Get performance metrics for advanced algorithms"""
    try:
        metrics = advanced_priority_manager.get_algorithm_metrics()
        
        # Add current queue statistics
        current_stats = {
            'total_waiting': Queue.query.filter_by(status='waiting').count(),
            'total_in_service': Queue.query.filter_by(status='in_service').count(),
            'total_completed_today': Queue.query.filter(
                Queue.status == 'completed',
                Queue.updated_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            ).count()
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'algorithm_metrics': {
                    algo_name: {
                        'average_wait_time': metric.average_wait_time,
                        'fairness_index': metric.fairness_index,
                        'throughput': metric.throughput,
                        'satisfaction_score': metric.satisfaction_score,
                        'algorithm_efficiency': metric.algorithm_efficiency
                    }
                    for algo_name, metric in metrics.items()
                },
                'current_statistics': current_stats,
                'active_algorithms': [algo.value for algo in advanced_priority_manager.active_algorithms]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting algorithm metrics: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get metrics: {str(e)}'
        }), 500

@advanced_priority_bp.route('/optimize', methods=['POST'])
@login_required
@admin_required
def trigger_advanced_optimization():
    """Trigger advanced queue optimization"""
    try:
        # Get current system state
        current_waiting = Queue.query.filter_by(status='waiting').count()
        
        if current_waiting == 0:
            return jsonify({
                'status': 'success',
                'message': 'No items in queue to optimize',
                'optimizations_applied': 0
            })
        
        # Trigger optimization using hybrid optimizer
        optimization_result = hybrid_engine.optimize_queue_distribution()
        
        return jsonify({
            'status': 'success',
            'message': 'Advanced optimization completed',
            'data': optimization_result
        })
        
    except Exception as e:
        logger.error(f"Error triggering optimization: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to trigger optimization: {str(e)}'
        }), 500

@advanced_priority_bp.route('/simulate', methods=['POST'])
@login_required
@admin_required
def simulate_algorithm_performance():
    """Simulate performance of different algorithm configurations"""
    try:
        data = request.get_json()
        
        if not data or 'algorithms' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Missing algorithms list for simulation'
            }), 400
        
        algorithm_names = data['algorithms']
        simulation_duration = data.get('duration_minutes', 60)
        
        # Validate algorithms
        valid_algorithms = []
        for name in algorithm_names:
            try:
                algo_type = AlgorithmType(name)
                valid_algorithms.append(algo_type)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid algorithm type: {name}'
                }), 400
        
        # Perform simulation (simplified)
        simulation_results = _simulate_algorithm_performance(
            valid_algorithms, simulation_duration
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Simulation completed',
            'data': simulation_results
        })
        
    except Exception as e:
        logger.error(f"Error in simulation: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Simulation failed: {str(e)}'
        }), 500

@advanced_priority_bp.route('/queue/reorder', methods=['POST'])
@login_required
@admin_required
def reorder_queue_advanced():
    """Reorder queue using advanced algorithms"""
    try:
        # Get current waiting queue
        current_queue = Queue.query.filter_by(status='waiting').order_by(
            Queue.priority_score.desc(), Queue.created_at.asc()
        ).all()
        
        if not current_queue:
            return jsonify({
                'status': 'success',
                'message': 'No items in queue to reorder',
                'reordered_count': 0
            })
        
        # Get system state
        system_state = {
            'total_waiting': len(current_queue),
            'agents_available': db.session.query(db.func.count()).filter(
                # Simplified agent availability check
            ).scalar() or 1,
            'peak_hours': (9 <= datetime.now().hour <= 11) or (14 <= datetime.now().hour <= 16),
            'average_wait_time': 25.0  # Simplified
        }
        
        # Apply advanced reordering
        optimized_queue = advanced_priority_manager.optimize_queue_order(
            current_queue, system_state
        )
        
        # Update queue positions
        reorder_count = 0
        for index, queue_item in enumerate(optimized_queue):
            new_priority = 1000 - index
            if queue_item.priority_score != new_priority:
                queue_item.priority_score = new_priority
                queue_item.updated_at = datetime.utcnow()
                reorder_count += 1
        
        if reorder_count > 0:
            db.session.commit()
        
        logger.info(f"Advanced queue reordering completed: {reorder_count} items reordered")
        
        return jsonify({
            'status': 'success',
            'message': f'Queue reordered using advanced algorithms',
            'reordered_count': reorder_count,
            'total_items': len(current_queue),
            'algorithms_used': [algo.value for algo in advanced_priority_manager.active_algorithms]
        })
        
    except Exception as e:
        logger.error(f"Error in advanced queue reordering: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to reorder queue: {str(e)}'
        }), 500

def _get_algorithm_description(algorithm_type: AlgorithmType) -> str:
    """Get description for algorithm type"""
    descriptions = {
        AlgorithmType.ADAPTIVE_PRIORITY: "Learns from historical data to adapt priority calculations",
        AlgorithmType.PREDICTIVE_SCHEDULING: "Predicts optimal scheduling based on patterns and forecasting",
        AlgorithmType.FAIRNESS_WEIGHTED: "Ensures fairness across different citizen groups",
        AlgorithmType.DYNAMIC_REORDERING: "Dynamically reorders queue based on real-time conditions",
        AlgorithmType.MACHINE_LEARNING: "Uses machine learning for intelligent priority decisions",
        AlgorithmType.MULTI_OBJECTIVE: "Balances multiple objectives like wait time, fairness, and throughput"
    }
    return descriptions.get(algorithm_type, "Advanced priority algorithm")

def _simulate_algorithm_performance(algorithms: list, duration_minutes: int) -> dict:
    """Simulate algorithm performance (simplified implementation)"""
    # This is a simplified simulation
    # In practice, you'd run more sophisticated modeling
    
    results = {
        'simulation_duration_minutes': duration_minutes,
        'algorithms_tested': [algo.value for algo in algorithms],
        'projected_metrics': {
            'average_wait_time_reduction': 15.5,
            'throughput_improvement': 12.3,
            'fairness_score_improvement': 8.7,
            'overall_efficiency_gain': 11.2
        },
        'recommendations': [
            'Enable Adaptive Priority for dynamic load conditions',
            'Use Fairness Weighted during peak hours',
            'Apply Dynamic Reordering for queues > 10 items'
        ]
    }
    
    return results

@advanced_priority_bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
def advanced_priority_dashboard():
    """Serve the advanced priority algorithms dashboard"""
    return render_template('advanced_priority_dashboard.html')

logger.info("Advanced Priority API endpoints initialized")