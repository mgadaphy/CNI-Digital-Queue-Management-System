from typing import Dict, Optional, List
from datetime import datetime
import logging

from ..models import Queue, ServiceType, Citizen, Agent
from .hybrid_optimizer import HybridOptimizationEngine, OptimizationResult
from .intelligent_assignment import intelligent_assignment, AssignmentStrategy, AssignmentResult
from .performance_monitor import metrics_collector, audit_manager, MetricType

logger = logging.getLogger(__name__)

# Initialize the hybrid optimization engine
hybrid_engine = HybridOptimizationEngine()

def calculate_priority_score(citizen: Citizen, service_type: ServiceType, 
                           special_factors: Dict = None) -> float:
    """Calculate a priority score for a citizen using the hybrid optimization engine.
    
    This function now uses the advanced Hybrid Optimization Engine for more
    sophisticated priority calculations that consider wait time, special needs,
    appointments, and system load.
    """
    try:
        # Use hybrid engine for advanced priority calculation
        wait_time_minutes = 0
        if hasattr(citizen, 'queue_entries'):
            latest_entry = Queue.query.filter_by(
                citizen_id=citizen.id, 
                status='waiting'
            ).order_by(Queue.created_at.desc()).first()
            
            if latest_entry:
                wait_time_minutes = int(
                    (datetime.utcnow() - latest_entry.created_at).total_seconds() / 60
                )
        
        priority_score = hybrid_engine.priority_matrix.calculate_priority_score(
            citizen, service_type, wait_time_minutes, special_factors
        )
        
        logger.debug(f"Advanced priority score calculated: {priority_score} for citizen {citizen.id}")
        return priority_score
        
    except Exception as e:
        logger.error(f"Error in advanced priority calculation: {e}. Falling back to simple calculation.")
        # Fallback to simple calculation
        base_priority = service_type.priority_level * 10
        return float(base_priority)

def get_next_citizen_in_queue():
    """Find the next citizen to be served based on the highest priority score.

    Returns the queue entry for the citizen with the highest priority score
    who is currently 'waiting'. Now uses advanced optimization for better results.
    """
    start_time = datetime.utcnow()
    try:
        # Trigger queue reoptimization periodically
        last_optimization = getattr(get_next_citizen_in_queue, '_last_optimization', None)
        current_time = datetime.utcnow()
        
        if (last_optimization is None or 
            (current_time - last_optimization).total_seconds() > 300):  # 5 minutes
            
            logger.info("Triggering queue reoptimization")
            hybrid_engine.reoptimize_queue()
            get_next_citizen_in_queue._last_optimization = current_time
            
            # Record reoptimization metric
            metrics_collector.record_metric(
                MetricType.SYSTEM_PERFORMANCE,
                'queue_reoptimization',
                1,
                'count',
                metadata={'trigger': 'periodic'}
            )
        
        # Get next citizen with highest priority
        next_in_queue = Queue.query.filter_by(status='waiting')\
            .order_by(Queue.priority_score.desc(), Queue.created_at.asc())\
            .first()
        
        # Record performance metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        metrics_collector.record_metric(
            MetricType.RESPONSE_TIME,
            'next_citizen_selection',
            processing_time,
            'ms'
        )
        
        if next_in_queue:
            # Calculate current wait time
            wait_time = (current_time - next_in_queue.created_at).total_seconds() / 60
            
            # Record wait time metric
            metrics_collector.record_metric(
                MetricType.BUSINESS_METRIC,
                'queue_wait_time',
                wait_time,
                'minutes',
                metadata={
                    'citizen_id': next_in_queue.citizen_id,
                    'priority_score': next_in_queue.priority_score
                }
            )
            
            logger.info(f"Next citizen selected: {next_in_queue.citizen_id} "
                       f"with priority {next_in_queue.priority_score}")
        
        return next_in_queue
        
    except Exception as e:
        # Record error metric
        metrics_collector.record_metric(
            MetricType.ERROR_RATE,
            'queue_selection_errors',
            1,
            'count',
            metadata={'error': str(e)}
        )
        
        logger.error(f"Error in advanced queue selection: {e}. Using fallback method.")
        # Fallback to simple query
        return Queue.query.filter_by(status='waiting')\
            .order_by(Queue.priority_score.desc(), Queue.created_at.asc())\
            .first()

def process_citizen_checkin(citizen: Citizen, service_type: ServiceType, 
                          special_factors: Dict = None) -> OptimizationResult:
    """Process citizen check-in using the Hybrid Optimization Engine.
    
    This function provides the full optimization experience including:
    - Advanced priority calculation
    - Intelligent agent assignment
    - Wait time estimation
    - Queue position calculation
    """
    start_time = datetime.utcnow()
    try:
        result = hybrid_engine.process_checkin(citizen, service_type, special_factors)
        
        # Record performance metrics
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        metrics_collector.record_metric(
            MetricType.RESPONSE_TIME,
            'citizen_checkin_processing',
            processing_time,
            'ms',
            metadata={
                'citizen_id': citizen.id,
                'service_type': service_type.code,
                'has_special_factors': special_factors is not None
            }
        )
        
        # Record business metrics
        metrics_collector.record_metric(
            MetricType.BUSINESS_METRIC,
            'estimated_wait_time',
            result.estimated_wait_time,
            'minutes',
            metadata={
                'citizen_id': citizen.id,
                'priority_score': result.priority_score,
                'queue_position': result.queue_position
            }
        )
        
        # Update queue length metric
        current_queue_length = Queue.query.filter_by(status='waiting').count()
        metrics_collector.record_metric(
            MetricType.SYSTEM_PERFORMANCE,
            'queue_length',
            current_queue_length,
            'count'
        )
        
        # Log audit trail
        audit_manager.log_event(
            event_type='citizen_checkin',
            entity_type='citizen',
            entity_id=citizen.id,
            user_id=None,  # System operation
            action='process_checkin',
            details={
                'service_type': service_type.code,
                'priority_score': result.priority_score,
                'estimated_wait_time': result.estimated_wait_time,
                'recommended_agent_id': result.recommended_agent_id,
                'special_factors': special_factors,
                'processing_time_ms': processing_time
            }
        )
        
        logger.info(f"Citizen {citizen.id} check-in processed. "
                   f"Recommended agent: {result.recommended_agent_id}, "
                   f"Estimated wait: {result.estimated_wait_time} minutes")
        
        return result
        
    except Exception as e:
        # Record error metric
        metrics_collector.record_metric(
            MetricType.ERROR_RATE,
            'checkin_processing_errors',
            1,
            'count',
            metadata={
                'citizen_id': citizen.id,
                'service_type': service_type.code,
                'error': str(e)
            }
        )
        
        logger.error(f"Error in hybrid check-in processing: {e}")
        # Return basic result as fallback
        priority_score = calculate_priority_score(citizen, service_type, special_factors)
        
        return OptimizationResult(
            recommended_agent_id=None,
            estimated_wait_time=10,  # Default estimate
            priority_score=priority_score,
            queue_position=1,
            optimization_factors={'fallback': True}
        )

def get_system_performance_metrics() -> Dict:
    """Get current system performance metrics from the hybrid engine."""
    try:
        return hybrid_engine.get_performance_metrics()
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return {
            'error': 'Unable to retrieve metrics',
            'total_waiting': Queue.query.filter_by(status='waiting').count()
        }

def optimize_agent_assignment(service_type: ServiceType, 
                             strategy: AssignmentStrategy = AssignmentStrategy.HYBRID) -> Optional[int]:
    """Find the optimal agent for a specific service type."""
    try:
        system_state = hybrid_engine.load_balancer.get_system_state()
        return hybrid_engine.load_balancer.find_optimal_agent(service_type, system_state, strategy)
    except Exception as e:
        logger.error(f"Error in agent assignment optimization: {e}")
        return None

def get_intelligent_agent_assignment(service_type: ServiceType, 
                                   strategy: AssignmentStrategy = AssignmentStrategy.HYBRID,
                                   exclude_agents: List[int] = None) -> AssignmentResult:
    """Get detailed intelligent agent assignment with reasoning and alternatives."""
    try:
        return intelligent_assignment.find_best_agent(service_type, strategy, exclude_agents)
    except Exception as e:
        logger.error(f"Error in intelligent agent assignment: {e}")
        return AssignmentResult(
            agent_id=None,
            confidence_score=0.0,
            assignment_reason=f"Error: {str(e)}",
            alternative_agents=[],
            estimated_service_time=service_type.estimated_duration,
            workload_impact=0.0
        )

def get_agent_performance_metrics(agent_id: int, service_type_code: str = None) -> Dict:
    """Get performance metrics for a specific agent."""
    try:
        performance_score = intelligent_assignment.performance_analyzer.get_agent_performance_score(
            agent_id, service_type_code
        )
        
        specialization_strength = 0.0
        if service_type_code:
            specialization_strength = intelligent_assignment.performance_analyzer.get_agent_specialization_strength(
                agent_id, service_type_code
            )
        
        current_workload = intelligent_assignment.workload_analyzer.get_agent_current_workload(agent_id)
        
        return {
            'agent_id': agent_id,
            'performance_score': performance_score,
            'specialization_strength': specialization_strength,
            'current_workload': current_workload,
            'service_type': service_type_code
        }
    except Exception as e:
        logger.error(f"Error getting agent performance metrics: {e}")
        return {'error': str(e)}

def get_assignment_analytics() -> Dict:
    """Get analytics about assignment patterns and system performance."""
    try:
        return intelligent_assignment.get_assignment_analytics()
    except Exception as e:
        logger.error(f"Error getting assignment analytics: {e}")
        return {'error': str(e)}

def evaluate_all_agents_for_service(service_type: ServiceType) -> List[Dict]:
    """Evaluate all available agents for a service type and return ranked list."""
    try:
        available_agents = Agent.query.filter(
            Agent.status == 'available',
            Agent.is_active == True
        ).all()
        
        agent_evaluations = []
        for agent in available_agents:
            capability = intelligent_assignment.evaluate_agent_capability(
                agent, service_type, AssignmentStrategy.HYBRID
            )
            
            agent_evaluations.append({
                'agent_id': agent.id,
                'agent_name': f"{agent.first_name} {agent.last_name}",
                'employee_id': agent.employee_id,
                'total_score': capability.total_score,
                'specialization_match': capability.specialization_match,
                'performance_score': capability.performance_score,
                'current_workload': capability.current_workload,
                'availability_score': capability.availability_score
            })
        
        # Sort by total score (descending)
        agent_evaluations.sort(key=lambda x: x['total_score'], reverse=True)
        
        return agent_evaluations
        
    except Exception as e:
        logger.error(f"Error evaluating agents for service: {e}")
        return []
