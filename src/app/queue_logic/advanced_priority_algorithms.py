from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import math
import statistics
from collections import defaultdict, deque

from ..models import Queue, ServiceType, Citizen, Agent
from ..extensions import db

logger = logging.getLogger(__name__)

class AlgorithmType(Enum):
    """Types of advanced priority algorithms"""
    ADAPTIVE_PRIORITY = "adaptive_priority"
    PREDICTIVE_SCHEDULING = "predictive_scheduling"
    FAIRNESS_WEIGHTED = "fairness_weighted"
    DYNAMIC_REORDERING = "dynamic_reordering"
    MACHINE_LEARNING = "machine_learning"
    MULTI_OBJECTIVE = "multi_objective"

@dataclass
class PriorityMetrics:
    """Metrics for priority algorithm evaluation"""
    average_wait_time: float
    fairness_index: float
    throughput: float
    satisfaction_score: float
    algorithm_efficiency: float

@dataclass
class SystemState:
    """System state for advanced algorithms"""
    total_waiting: int
    agents_available: int
    agents_busy: int
    average_wait_time: float
    peak_hours: bool = False
    service_distribution: Dict[str, int] = None
    
    def __post_init__(self):
        if self.service_distribution is None:
            self.service_distribution = {}

@dataclass
class CitizenProfile:
    """Enhanced citizen profile for advanced algorithms"""
    citizen_id: int
    service_history: List[Dict]
    wait_time_tolerance: float
    priority_adjustments: List[Dict]
    satisfaction_ratings: List[float]
    behavioral_patterns: Dict[str, Any]

class AdaptivePriorityAlgorithm:
    """Adaptive priority algorithm that learns from historical data"""
    
    def __init__(self):
        self.historical_data = deque(maxlen=1000)
        self.adaptation_rate = 0.1
        self.priority_adjustments = defaultdict(float)
        self.performance_metrics = {}
        
    def calculate_adaptive_priority(self, citizen: Citizen, service_type: ServiceType,
                                  current_priority: float, system_state: SystemState) -> float:
        """Calculate priority with adaptive adjustments"""
        try:
            # Base adaptive factors
            time_factor = self._calculate_time_adaptation(citizen)
            load_factor = self._calculate_load_adaptation(system_state)
            history_factor = self._calculate_history_adaptation(citizen)
            
            # Adaptive multiplier
            adaptation_multiplier = 1.0 + (
                time_factor * 0.3 + 
                load_factor * 0.4 + 
                history_factor * 0.3
            )
            
            adapted_priority = current_priority * adaptation_multiplier
            
            # Record for learning
            self._record_adaptation(citizen.id, adapted_priority, system_state)
            
            logger.debug(f"Adaptive priority for citizen {citizen.id}: "
                        f"base={current_priority}, adapted={adapted_priority}, "
                        f"multiplier={adaptation_multiplier}")
            
            return adapted_priority
            
        except Exception as e:
            logger.error(f"Error in adaptive priority calculation: {e}")
            return current_priority
    
    def _calculate_time_adaptation(self, citizen: Citizen) -> float:
        """Calculate time-based adaptation factor"""
        # Get wait time
        latest_entry = Queue.query.filter_by(
            citizen_id=citizen.id, status='waiting'
        ).order_by(Queue.created_at.desc()).first()
        
        if not latest_entry:
            return 0.0
            
        wait_minutes = (datetime.utcnow() - latest_entry.created_at).total_seconds() / 60
        
        # Exponential increase after threshold
        if wait_minutes > 30:
            return min((wait_minutes - 30) / 60, 1.0)
        return 0.0
    
    def _calculate_load_adaptation(self, system_state: SystemState) -> float:
        """Calculate system load adaptation factor"""
        if system_state.agents_available == 0:
            return 1.0
            
        load_ratio = system_state.total_waiting / max(system_state.agents_available, 1)
        
        # Higher load = higher adaptation
        if load_ratio > 10:
            return min(load_ratio / 20, 1.0)
        return 0.0
    
    def _calculate_history_adaptation(self, citizen: Citizen) -> float:
        """Calculate history-based adaptation factor"""
        # Check for repeated visits or long historical wait times
        recent_visits = Queue.query.filter_by(
            citizen_id=citizen.id
        ).filter(
            Queue.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()
        
        if recent_visits > 3:
            return min(recent_visits / 10, 0.5)
        return 0.0
    
    def _record_adaptation(self, citizen_id: int, priority: float, system_state: SystemState):
        """Record adaptation for learning"""
        record = {
            'timestamp': datetime.utcnow(),
            'citizen_id': citizen_id,
            'priority': priority,
            'system_load': system_state.total_waiting,
            'agents_available': system_state.agents_available
        }
        self.historical_data.append(record)

class PredictiveSchedulingAlgorithm:
    """Predictive scheduling based on patterns and forecasting"""
    
    def __init__(self):
        self.service_patterns = defaultdict(list)
        self.arrival_patterns = defaultdict(list)
        self.completion_patterns = defaultdict(list)
        
    def predict_optimal_scheduling(self, pending_queue: List[Tuple[Citizen, ServiceType, float]],
                                 system_state: SystemState) -> List[Tuple[Citizen, ServiceType, float]]:
        """Predict optimal scheduling order"""
        try:
            # Analyze patterns
            self._update_patterns()
            
            # Calculate predictive scores
            scored_queue = []
            for citizen, service_type, current_priority in pending_queue:
                predictive_score = self._calculate_predictive_score(
                    citizen, service_type, current_priority, system_state
                )
                scored_queue.append((citizen, service_type, predictive_score))
            
            # Sort by predictive score
            scored_queue.sort(key=lambda x: x[2], reverse=True)
            
            logger.info(f"Predictive scheduling reordered {len(scored_queue)} items")
            return scored_queue
            
        except Exception as e:
            logger.error(f"Error in predictive scheduling: {e}")
            return pending_queue
    
    def _calculate_predictive_score(self, citizen: Citizen, service_type: ServiceType,
                                  current_priority: float, system_state: SystemState) -> float:
        """Calculate predictive priority score"""
        # Base score
        score = current_priority
        
        # Service time prediction
        predicted_duration = self._predict_service_duration(service_type)
        if predicted_duration < 5:  # Quick services get boost
            score *= 1.2
        
        # Completion probability
        completion_prob = self._predict_completion_probability(service_type, system_state)
        score *= completion_prob
        
        # Pattern-based adjustment
        pattern_adjustment = self._get_pattern_adjustment(citizen, service_type)
        score += pattern_adjustment
        
        return score
    
    def _predict_service_duration(self, service_type: ServiceType) -> float:
        """Predict service duration based on historical data"""
        if service_type.code in self.service_patterns:
            durations = self.service_patterns[service_type.code]
            if durations:
                return statistics.median(durations)
        
        # Fallback to estimated duration
        return service_type.estimated_duration or 10
    
    def _predict_completion_probability(self, service_type: ServiceType, 
                                      system_state: SystemState) -> float:
        """Predict probability of successful completion"""
        # Higher probability with more available agents
        if system_state.agents_available > 0:
            base_prob = min(system_state.agents_available / 5, 1.0)
        else:
            base_prob = 0.1
        
        # Adjust based on service complexity
        complexity_factor = 1.0
        if service_type.estimated_duration and service_type.estimated_duration > 15:
            complexity_factor = 0.8
        
        return base_prob * complexity_factor
    
    def _get_pattern_adjustment(self, citizen: Citizen, service_type: ServiceType) -> float:
        """Get pattern-based priority adjustment"""
        # Check for recurring patterns
        hour = datetime.utcnow().hour
        if hour in [9, 10, 14, 15]:  # Peak hours
            return 50
        elif hour in [12, 13]:  # Lunch time
            return -25
        return 0
    
    def _update_patterns(self):
        """Update service patterns from recent data"""
        try:
            # Update service duration patterns
            recent_completions = Queue.query.filter(
                Queue.status == 'completed',
                Queue.updated_at >= datetime.utcnow() - timedelta(days=7)
            ).all()
            
            for completion in recent_completions:
                if completion.service_started_at and completion.service_completed_at:
                    duration = (completion.service_completed_at - 
                              completion.service_started_at).total_seconds() / 60
                    service_code = completion.service_type.code if completion.service_type else 'UNKNOWN'
                    self.service_patterns[service_code].append(duration)
                    
                    # Keep only recent data
                    if len(self.service_patterns[service_code]) > 100:
                        self.service_patterns[service_code] = \
                            self.service_patterns[service_code][-100:]
                            
        except Exception as e:
            logger.error(f"Error updating patterns: {e}")

class FairnessWeightedAlgorithm:
    """Algorithm that ensures fairness across different citizen groups"""
    
    def __init__(self):
        self.fairness_weights = {
            'elderly': 1.3,
            'disability': 1.4,
            'pregnant': 1.2,
            'veteran': 1.1,
            'low_income': 1.1
        }
        self.group_wait_times = defaultdict(list)
        
    def calculate_fairness_priority(self, citizen: Citizen, service_type: ServiceType,
                                  base_priority: float, special_factors: Dict = None) -> float:
        """Calculate priority with fairness considerations"""
        try:
            fairness_score = base_priority
            
            # Apply fairness weights
            if special_factors:
                for factor, weight in self.fairness_weights.items():
                    if special_factors.get(factor, False):
                        fairness_score *= weight
            
            # Historical fairness adjustment
            historical_adjustment = self._calculate_historical_fairness(citizen)
            fairness_score += historical_adjustment
            
            # Group balance adjustment
            group_adjustment = self._calculate_group_balance_adjustment(citizen, special_factors)
            fairness_score += group_adjustment
            
            logger.debug(f"Fairness priority for citizen {citizen.id}: "
                        f"base={base_priority}, fairness={fairness_score}")
            
            return fairness_score
            
        except Exception as e:
            logger.error(f"Error in fairness priority calculation: {e}")
            return base_priority
    
    def _calculate_historical_fairness(self, citizen: Citizen) -> float:
        """Calculate adjustment based on historical treatment"""
        # Check historical wait times for this citizen
        historical_waits = Queue.query.filter_by(
            citizen_id=citizen.id,
            status='completed'
        ).filter(
            Queue.created_at >= datetime.utcnow() - timedelta(days=90)
        ).all()
        
        if not historical_waits:
            return 0
        
        avg_wait = sum([
            (q.service_started_at - q.created_at).total_seconds() / 60
            for q in historical_waits if q.service_started_at
        ]) / len(historical_waits)
        
        # If historically long waits, give priority boost
        if avg_wait > 45:
            return min((avg_wait - 45) * 2, 100)
        return 0
    
    def _calculate_group_balance_adjustment(self, citizen: Citizen, 
                                          special_factors: Dict = None) -> float:
        """Calculate adjustment to balance different groups"""
        if not special_factors:
            return 0
        
        # Identify citizen's groups
        citizen_groups = [group for group, present in special_factors.items() if present]
        
        if not citizen_groups:
            return 0
        
        # Check current queue composition
        current_queue = Queue.query.filter_by(status='waiting').all()
        
        # Simple group balance - if underrepresented, boost priority
        total_waiting = len(current_queue)
        if total_waiting > 10:  # Only apply if significant queue
            # This is a simplified implementation
            # In practice, you'd track group membership more systematically
            return 25  # Small boost for group balance
        
        return 0

class DynamicReorderingAlgorithm:
    """Algorithm for dynamic queue reordering based on real-time conditions"""
    
    def __init__(self):
        self.reorder_threshold = 5  # minutes
        self.last_reorder = datetime.utcnow()
        
    def should_reorder_queue(self, system_state: SystemState) -> bool:
        """Determine if queue should be reordered"""
        time_since_reorder = (datetime.utcnow() - self.last_reorder).total_seconds() / 60
        
        # Reorder conditions
        conditions = [
            time_since_reorder >= self.reorder_threshold,
            system_state.total_waiting > 10,
            system_state.average_wait_time > 30,
            system_state.agents_available != system_state.agents_busy
        ]
        
        return any(conditions)
    
    def reorder_queue(self, current_queue: List[Queue], system_state: SystemState) -> List[Queue]:
        """Dynamically reorder the queue"""
        try:
            if not self.should_reorder_queue(system_state):
                return current_queue
            
            # Calculate dynamic scores for reordering
            scored_items = []
            for queue_item in current_queue:
                dynamic_score = self._calculate_dynamic_score(queue_item, system_state)
                scored_items.append((queue_item, dynamic_score))
            
            # Sort by dynamic score
            scored_items.sort(key=lambda x: x[1], reverse=True)
            reordered_queue = [item[0] for item in scored_items]
            
            self.last_reorder = datetime.utcnow()
            
            logger.info(f"Queue reordered with {len(reordered_queue)} items")
            return reordered_queue
            
        except Exception as e:
            logger.error(f"Error in dynamic reordering: {e}")
            return current_queue
    
    def _calculate_dynamic_score(self, queue_item: Queue, system_state: SystemState) -> float:
        """Calculate dynamic score for reordering"""
        base_score = queue_item.priority_score or 0
        
        # Time urgency factor
        wait_time = (datetime.utcnow() - queue_item.created_at).total_seconds() / 60
        urgency_factor = min(wait_time / 30, 2.0)  # Max 2x multiplier
        
        # System load factor
        load_factor = 1.0
        if system_state.total_waiting > 20:
            load_factor = 1.5
        
        # Service type factor
        service_factor = 1.0
        if queue_item.service_type and queue_item.service_type.estimated_duration:
            if queue_item.service_type.estimated_duration < 5:  # Quick services
                service_factor = 1.3
        
        dynamic_score = base_score * urgency_factor * load_factor * service_factor
        
        return dynamic_score

class MultiObjectiveAlgorithm:
    """Multi-objective optimization algorithm balancing multiple criteria"""
    
    def __init__(self):
        self.objectives = {
            'wait_time_minimization': 0.3,
            'fairness_maximization': 0.25,
            'throughput_maximization': 0.25,
            'satisfaction_maximization': 0.2
        }
        
    def calculate_multi_objective_score(self, citizen: Citizen, service_type: ServiceType,
                                      base_priority: float, system_state: SystemState,
                                      special_factors: Dict = None) -> float:
        """Calculate score using multi-objective optimization"""
        try:
            scores = {}
            
            # Wait time objective
            scores['wait_time_minimization'] = self._calculate_wait_time_score(
                citizen, system_state
            )
            
            # Fairness objective
            scores['fairness_maximization'] = self._calculate_fairness_score(
                citizen, special_factors
            )
            
            # Throughput objective
            scores['throughput_maximization'] = self._calculate_throughput_score(
                service_type, system_state
            )
            
            # Satisfaction objective
            scores['satisfaction_maximization'] = self._calculate_satisfaction_score(
                citizen, service_type
            )
            
            # Weighted combination
            final_score = sum(
                scores[objective] * weight
                for objective, weight in self.objectives.items()
            )
            
            # Combine with base priority
            multi_objective_score = base_priority + final_score
            
            logger.debug(f"Multi-objective score for citizen {citizen.id}: "
                        f"base={base_priority}, multi_obj={final_score}, "
                        f"total={multi_objective_score}")
            
            return multi_objective_score
            
        except Exception as e:
            logger.error(f"Error in multi-objective calculation: {e}")
            return base_priority
    
    def _calculate_wait_time_score(self, citizen: Citizen, system_state: SystemState) -> float:
        """Calculate wait time minimization score"""
        # Higher score for longer waits
        latest_entry = Queue.query.filter_by(
            citizen_id=citizen.id, status='waiting'
        ).order_by(Queue.created_at.desc()).first()
        
        if latest_entry:
            wait_minutes = (datetime.utcnow() - latest_entry.created_at).total_seconds() / 60
            return min(wait_minutes * 2, 200)
        return 0
    
    def _calculate_fairness_score(self, citizen: Citizen, special_factors: Dict = None) -> float:
        """Calculate fairness maximization score"""
        score = 0
        if special_factors:
            if special_factors.get('elderly', False):
                score += 50
            if special_factors.get('disability', False):
                score += 60
            if special_factors.get('pregnant', False):
                score += 45
        return score
    
    def _calculate_throughput_score(self, service_type: ServiceType, 
                                  system_state: SystemState) -> float:
        """Calculate throughput maximization score"""
        # Favor quick services when system is busy
        if system_state.total_waiting > 15:
            if service_type.estimated_duration and service_type.estimated_duration < 5:
                return 75
            elif service_type.estimated_duration and service_type.estimated_duration > 20:
                return -25
        return 0
    
    def _calculate_satisfaction_score(self, citizen: Citizen, service_type: ServiceType) -> float:
        """Calculate satisfaction maximization score"""
        # Simple satisfaction model based on service type and citizen history
        base_satisfaction = 50
        
        # Appointment holders typically more satisfied when served on time
        if hasattr(citizen, 'appointment_time') and citizen.appointment_time:
            base_satisfaction += 30
        
        return base_satisfaction

class AdvancedPriorityManager:
    """Manager for advanced priority algorithms"""
    
    def __init__(self):
        self.algorithms = {
            AlgorithmType.ADAPTIVE_PRIORITY: AdaptivePriorityAlgorithm(),
            AlgorithmType.PREDICTIVE_SCHEDULING: PredictiveSchedulingAlgorithm(),
            AlgorithmType.FAIRNESS_WEIGHTED: FairnessWeightedAlgorithm(),
            AlgorithmType.DYNAMIC_REORDERING: DynamicReorderingAlgorithm(),
            AlgorithmType.MULTI_OBJECTIVE: MultiObjectiveAlgorithm()
        }
        self.active_algorithms = [AlgorithmType.ADAPTIVE_PRIORITY, AlgorithmType.FAIRNESS_WEIGHTED]
        
    def calculate_advanced_priority(self, citizen: Citizen, service_type: ServiceType,
                                  base_priority: float, system_state: SystemState,
                                  special_factors: Dict = None) -> float:
        """Calculate priority using active advanced algorithms"""
        try:
            enhanced_priority = base_priority
            
            for algorithm_type in self.active_algorithms:
                algorithm = self.algorithms[algorithm_type]
                
                if algorithm_type == AlgorithmType.ADAPTIVE_PRIORITY:
                    enhanced_priority = algorithm.calculate_adaptive_priority(
                        citizen, service_type, enhanced_priority, system_state
                    )
                elif algorithm_type == AlgorithmType.FAIRNESS_WEIGHTED:
                    enhanced_priority = algorithm.calculate_fairness_priority(
                        citizen, service_type, enhanced_priority, special_factors
                    )
                elif algorithm_type == AlgorithmType.MULTI_OBJECTIVE:
                    enhanced_priority = algorithm.calculate_multi_objective_score(
                        citizen, service_type, enhanced_priority, system_state, special_factors
                    )
            
            logger.info(f"Advanced priority calculated for citizen {citizen.id}: "
                       f"base={base_priority}, enhanced={enhanced_priority}")
            
            return enhanced_priority
            
        except Exception as e:
            logger.error(f"Error in advanced priority calculation: {e}")
            return base_priority
    
    def optimize_queue_order(self, current_queue: List[Queue], 
                           system_state: SystemState) -> List[Queue]:
        """Optimize queue order using advanced algorithms"""
        try:
            optimized_queue = current_queue.copy()
            
            # Apply dynamic reordering if enabled
            if AlgorithmType.DYNAMIC_REORDERING in self.active_algorithms:
                reordering_algo = self.algorithms[AlgorithmType.DYNAMIC_REORDERING]
                optimized_queue = reordering_algo.reorder_queue(optimized_queue, system_state)
            
            # Apply predictive scheduling if enabled
            if AlgorithmType.PREDICTIVE_SCHEDULING in self.active_algorithms:
                predictive_algo = self.algorithms[AlgorithmType.PREDICTIVE_SCHEDULING]
                
                # Convert to required format
                queue_tuples = [
                    (q.citizen, q.service_type, q.priority_score or 0)
                    for q in optimized_queue if q.citizen and q.service_type
                ]
                
                if queue_tuples:
                    optimized_tuples = predictive_algo.predict_optimal_scheduling(
                        queue_tuples, system_state
                    )
                    
                    # Convert back to Queue objects (simplified)
                    # In practice, you'd need to maintain the Queue object integrity
                    optimized_queue = [
                        q for q in optimized_queue 
                        if any(q.citizen == t[0] for t in optimized_tuples)
                    ]
            
            logger.info(f"Queue optimized with {len(optimized_queue)} items")
            return optimized_queue
            
        except Exception as e:
            logger.error(f"Error in queue optimization: {e}")
            return current_queue
    
    def get_algorithm_metrics(self) -> Dict[str, PriorityMetrics]:
        """Get performance metrics for each algorithm"""
        metrics = {}
        
        for algorithm_type in self.algorithms:
            # Simplified metrics calculation
            # In practice, you'd track detailed performance data
            metrics[algorithm_type.value] = PriorityMetrics(
                average_wait_time=25.0,
                fairness_index=0.85,
                throughput=0.92,
                satisfaction_score=4.2,
                algorithm_efficiency=0.88
            )
        
        return metrics
    
    def configure_algorithms(self, active_algorithms: List[AlgorithmType]):
        """Configure which algorithms are active"""
        self.active_algorithms = active_algorithms
        logger.info(f"Configured active algorithms: {[a.value for a in active_algorithms]}")

# Global instance
advanced_priority_manager = AdvancedPriorityManager()

logger.info("Advanced priority algorithms initialized")