from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from ..models import Queue, ServiceType, Citizen, Agent
from ..extensions import db
from .intelligent_assignment import intelligent_assignment, AssignmentStrategy
from .advanced_priority_algorithms import advanced_priority_manager, AlgorithmType, SystemState
from .queue_config import get_queue_config
from ..utils.db_transaction_manager import get_transaction_manager, optimized_transaction
from ..utils.queue_logger import performance_monitor, queue_operation_logger
from ..utils.config_manager import get_queue_optimization_config
from ..utils.performance_metrics import get_performance_collector, record_performance_metric

logger = logging.getLogger(__name__)

class PriorityLevel(Enum):
    """Priority levels for queue management"""
    EMERGENCY = 1
    APPOINTMENT = 2
    COLLECTION = 3
    RENEWAL = 4
    NEW_APPLICATION = 5
    CORRECTION = 6

# SystemState is now imported from advanced_priority_algorithms

@dataclass
class OptimizationResult:
    """Result of queue optimization"""
    recommended_agent_id: Optional[int]
    estimated_wait_time: int
    priority_score: float
    queue_position: int
    optimization_factors: Dict[str, float]

class PriorityMatrix:
    """Advanced priority calculation matrix"""
    
    PRIORITY_WEIGHTS = {
        PriorityLevel.EMERGENCY: 1000,
        PriorityLevel.APPOINTMENT: 800,
        PriorityLevel.COLLECTION: 600,
        PriorityLevel.RENEWAL: 400,
        PriorityLevel.NEW_APPLICATION: 200,
        PriorityLevel.CORRECTION: 100
    }
    
    SERVICE_TIME_ESTIMATES = {
        'COLLECTION': 3,
        'RENEWAL': 10,
        'NEW_APPLICATION': 15,
        'CORRECTION': 20,
        'EMERGENCY': 12,
        'APPOINTMENT': 8
    }
    
    def calculate_priority_score(self, citizen: Citizen, service_type: ServiceType, 
                               wait_time_minutes: int = 0, special_factors: Dict = None) -> float:
        """Calculate comprehensive priority score with advanced algorithms and configurable weights"""
        config = get_queue_optimization_config()
        
        base_priority = self.PRIORITY_WEIGHTS.get(
            PriorityLevel(service_type.priority_level), 100
        )
        
        # Wait time bonus with configurable weight
        wait_bonus = min(wait_time_minutes * config.get('wait_time_weight', 2), 200)
        
        # Special needs bonus with configurable weight
        special_bonus = 0
        if special_factors:
            demographic_weight = config.get('demographic_weight', 1.0)
            if special_factors.get('elderly', False):
                special_bonus += int(100 * demographic_weight)
            if special_factors.get('disability', False):
                special_bonus += int(150 * demographic_weight)
            if special_factors.get('pregnant', False):
                special_bonus += int(120 * demographic_weight)
        
        # Appointment bonus with configurable weight
        appointment_bonus = 0
        if hasattr(citizen, 'appointment_time') and citizen.appointment_time:
            appointment_bonus = int(300 * config.get('citizen_priority_weight', 1.0))
        
        traditional_score = base_priority + wait_bonus + special_bonus + appointment_bonus
        
        # Apply advanced priority algorithms with configuration
        try:
            system_state = {
                'total_waiting': Queue.query.filter_by(status='waiting').count(),
                'peak_hours': (9 <= datetime.now().hour <= 11) or (14 <= datetime.now().hour <= 16)
            }
            enhanced_score = advanced_priority_manager.calculate_advanced_priority(
                citizen, service_type, traditional_score, system_state, special_factors
            )
            
            # Apply high priority threshold from config
            if enhanced_score > config.get('high_priority_threshold', 1000):
                enhanced_score *= 1.2  # Boost high priority items
            
            total_score = enhanced_score
        except Exception as e:
            logger.warning(f"Advanced priority calculation failed, using traditional: {e}")
            total_score = traditional_score
        
        logger.debug(f"Priority calculation for citizen {citizen.id}: "
                    f"base={base_priority}, wait={wait_bonus}, "
                    f"special={special_bonus}, appointment={appointment_bonus}, "
                    f"total={total_score}")
        
        return total_score

class DynamicLoadBalancer:
    """Dynamic load balancing for optimal agent assignment"""
    
    def __init__(self):
        self.agent_workloads = {}
        self.service_specializations = {}
    
    def get_system_state(self) -> SystemState:
        """Get current system state for optimization"""
        total_waiting = Queue.query.filter_by(status='waiting').count()
        
        # Get agent availability
        agents_available = Agent.query.filter_by(status='available').count()
        agents_busy = Agent.query.filter_by(status='busy').count()
        
        # Calculate average wait time
        waiting_queues = Queue.query.filter_by(status='waiting').all()
        if waiting_queues:
            wait_times = [(datetime.utcnow() - q.created_at).total_seconds() / 60 
                         for q in waiting_queues]
            average_wait_time = sum(wait_times) / len(wait_times)
        else:
            average_wait_time = 0.0
        
        # Check if peak hours (9-11 AM, 2-4 PM)
        current_hour = datetime.now().hour
        peak_hours = (9 <= current_hour <= 11) or (14 <= current_hour <= 16)
        
        # Service distribution
        service_distribution = {}
        for service_type in ServiceType.query.all():
            count = Queue.query.filter_by(
                service_type_id=service_type.id, 
                status='waiting'
            ).count()
            service_distribution[service_type.code] = count
        
        return SystemState(
            total_waiting=total_waiting,
            agents_available=agents_available,
            agents_busy=agents_busy,
            average_wait_time=average_wait_time,
            peak_hours=peak_hours,
            service_distribution=service_distribution
        )
    
    def calculate_agent_workload(self, agent_id: int) -> float:
        """Calculate current workload for an agent"""
        # Count active queue entries assigned to agent
        active_count = Queue.query.filter_by(
            agent_id=agent_id, 
            status='in_progress'
        ).count()
        
        # Count waiting entries assigned to agent
        waiting_count = Queue.query.filter_by(
            agent_id=agent_id, 
            status='waiting'
        ).count()
        
        # Calculate workload score
        workload_score = (active_count * 2) + waiting_count
        
        return workload_score
    
    def find_optimal_agent(self, service_type: ServiceType, 
                          system_state: SystemState, 
                          strategy: AssignmentStrategy = AssignmentStrategy.HYBRID) -> Optional[int]:
        """Find optimal agent for service type using intelligent assignment"""
        try:
            # Use intelligent assignment system for enhanced agent selection
            assignment_result = intelligent_assignment.find_best_agent(
                service_type, strategy
            )
            
            if assignment_result.agent_id:
                logger.info(f"Intelligent assignment selected agent {assignment_result.agent_id}: "
                           f"{assignment_result.assignment_reason} "
                           f"(confidence: {assignment_result.confidence_score:.3f})")
                return assignment_result.agent_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error in intelligent agent assignment: {e}. Using fallback method.")
            
            # Fallback to simple assignment
            available_agents = Agent.query.filter_by(status='available').all()
            
            if not available_agents:
                return None
            
            best_agent = None
            best_score = float('inf')
            
            for agent in available_agents:
                # Check specialization match
                specialization_bonus = 0
                if hasattr(agent, 'specializations') and agent.specializations:
                    if service_type.code in agent.specializations:
                        specialization_bonus = -50  # Lower score is better
                
                # Calculate workload
                workload = self.calculate_agent_workload(agent.id)
                
                # Calculate total score (lower is better)
                total_score = workload - specialization_bonus
                
                if total_score < best_score:
                    best_score = total_score
                    best_agent = agent
            
            return best_agent.id if best_agent else None

class IntelligentRouter:
    """Intelligent routing for queue optimization"""
    
    def __init__(self):
        self.priority_matrix = PriorityMatrix()
        self.load_balancer = DynamicLoadBalancer()
    
    def estimate_wait_time(self, citizen: Citizen, service_type: ServiceType, 
                          system_state: SystemState) -> int:
        """Estimate wait time for citizen"""
        # Base service time
        base_time = self.priority_matrix.SERVICE_TIME_ESTIMATES.get(
            service_type.code, 10
        )
        
        # Queue position factor
        higher_priority_count = Queue.query.filter(
            Queue.status == 'waiting',
            Queue.priority_score > self.priority_matrix.calculate_priority_score(
                citizen, service_type
            )
        ).count()
        
        # Agent availability factor
        if system_state.agents_available > 0:
            agent_factor = 1.0
        else:
            agent_factor = 1.5  # 50% longer if no agents available
        
        # Peak hours factor
        peak_factor = 1.3 if system_state.peak_hours else 1.0
        
        estimated_time = int(
            (base_time + (higher_priority_count * base_time * 0.5)) * 
            agent_factor * peak_factor
        )
        
        return max(estimated_time, 1)  # Minimum 1 minute
    
    def calculate_queue_position(self, priority_score: float) -> int:
        """Calculate position in queue based on priority score"""
        higher_priority_count = Queue.query.filter(
            Queue.status == 'waiting',
            Queue.priority_score > priority_score
        ).count()
        
        return higher_priority_count + 1

class HybridOptimizationEngine:
    """Main hybrid optimization engine"""
    
    def __init__(self):
        self.priority_matrix = PriorityMatrix()
        self.load_balancer = DynamicLoadBalancer()
        self.routing_engine = IntelligentRouter()
        self.config = get_queue_optimization_config()
        
        # Configuration weights are already set in the dataclass with defaults
        # No need to set defaults as they're defined in QueueOptimizationConfig
        # Configure advanced algorithms
        try:
            advanced_priority_manager.configure_algorithms([
                AlgorithmType.ADAPTIVE_PRIORITY,
                AlgorithmType.FAIRNESS_WEIGHTED,
                AlgorithmType.DYNAMIC_REORDERING
            ])
            logger.info("Hybrid Optimization Engine initialized with advanced priority algorithms")
        except Exception as e:
            logger.warning(f"Failed to configure advanced algorithms: {e}")
            logger.info("Hybrid Optimization Engine initialized")
    
    def process_checkin(self, citizen: Citizen, service_type: ServiceType, 
                       special_factors: Dict = None) -> OptimizationResult:
        """Process citizen check-in and determine optimal queue assignment"""
        logger.info(f"Processing check-in for citizen {citizen.id}, service {service_type.code}")
        
        # Get current system state
        system_state = self.load_balancer.get_system_state()
        
        # Calculate priority score with wait time consideration
        wait_time_minutes = 0  # New check-in starts with 0 wait time
        priority_score = self.priority_matrix.calculate_priority_score(
            citizen, service_type, wait_time_minutes=wait_time_minutes, special_factors=special_factors
        )
        
        # Find optimal agent
        recommended_agent_id = self.load_balancer.find_optimal_agent(
            service_type, system_state
        )
        
        # Estimate wait time
        estimated_wait_time = self.routing_engine.estimate_wait_time(
            citizen, service_type, system_state
        )
        
        # Calculate queue position
        queue_position = self.routing_engine.calculate_queue_position(priority_score)
        
        # Optimization factors for transparency
        optimization_factors = {
            'priority_score': priority_score,
            'system_load': system_state.total_waiting,
            'agent_availability': system_state.agents_available,
            'peak_hours': system_state.peak_hours,
            'service_specialization': bool(recommended_agent_id)
        }
        
        result = OptimizationResult(
            recommended_agent_id=recommended_agent_id,
            estimated_wait_time=estimated_wait_time,
            priority_score=priority_score,
            queue_position=queue_position,
            optimization_factors=optimization_factors
        )
        
        logger.info(f"Optimization result: agent={recommended_agent_id}, "
                   f"wait_time={estimated_wait_time}, position={queue_position}")
        
        return result
    
    @performance_monitor('queue_optimization')
    @queue_operation_logger('optimization')
    @optimized_transaction(retry_on_failure=True)
    def optimize_queue(self, session, tickets: List) -> List:
        """Optimize a list of tickets using advanced algorithms with enhanced transaction handling"""
        logger.info(f"Optimizing queue with {len(tickets)} tickets")
        transaction_manager = get_transaction_manager()
        config = get_queue_config()
        
        # Record performance metrics
        performance_collector = get_performance_collector()
        start_time = datetime.utcnow()
        
        try:
            # Get current system state
            system_state = self.load_balancer.get_system_state()
            
            # Process tickets in batches using configuration values
            batch_size = getattr(config, 'OPTIMIZATION_BATCH_SIZE', self.config.get('optimization_batch_size', 50))
            enhanced_tickets = []
            changes_made = 0
            
            for i in range(0, len(tickets), batch_size):
                batch = tickets[i:i + batch_size]
                
                for ticket in batch:
                    if hasattr(ticket, 'citizen') and hasattr(ticket, 'service_type'):
                        # Calculate wait time
                        wait_time = datetime.utcnow() - ticket.created_at
                        wait_minutes = int(wait_time.total_seconds() / 60)
                        
                        # Calculate enhanced priority using advanced algorithms
                        old_priority = getattr(ticket, 'priority_score', 0)
                        enhanced_priority = self.priority_matrix.calculate_priority_score(
                            ticket.citizen, 
                            ticket.service_type, 
                            wait_time_minutes=wait_minutes
                        )
                        
                        # Update ticket priority and track changes
                        if abs(enhanced_priority - old_priority) > 10:  # Significant change threshold
                            changes_made += 1
                        ticket.priority_score = enhanced_priority
                        enhanced_tickets.append(ticket)
                    else:
                        # Keep original ticket if missing required attributes
                        enhanced_tickets.append(ticket)
                
                # Flush batch to database
                session.flush()
            
            # Sort by enhanced priority score (highest first)
            optimized_tickets = sorted(
                enhanced_tickets, 
                key=lambda t: getattr(t, 'priority_score', 0), 
                reverse=True
            )
            
            # Update queue positions
            for i, ticket in enumerate(optimized_tickets):
                ticket.queue_position = i + 1
            
            # Record performance metrics
            optimization_time = (datetime.utcnow() - start_time).total_seconds()
            performance_collector.record_optimization_result(
                optimization_time=optimization_time,
                changes_made=changes_made,
                efficiency_improvement=min(changes_made / len(tickets) * 100, 100) if tickets else 0,
                algorithm_used='hybrid',
                queue_size_before=len(tickets),
                queue_size_after=len(optimized_tickets)
            )
            
            record_performance_metric('queue_optimization_time', optimization_time, 'optimization')
            record_performance_metric('queue_changes_made', changes_made, 'optimization')
            
            logger.info(f"Queue optimization completed for {len(optimized_tickets)} tickets with {changes_made} changes")
            return optimized_tickets
            
        except Exception as e:
            logger.error(f"Error in optimize_queue: {str(e)}")
            raise
    
    @performance_monitor('queue_reoptimization')
    @queue_operation_logger('reoptimization')
    @optimized_transaction(retry_on_failure=True)
    def reoptimize_queue(self, session) -> List[Dict]:
        """Reoptimize entire queue with advanced algorithms using enhanced transaction handling"""
        logger.info("Starting queue reoptimization with advanced algorithms")
        transaction_manager = get_transaction_manager()
        
        waiting_entries = session.query(Queue).filter_by(status='waiting').all()
        optimization_results = []
        
        # Apply advanced queue optimization
        try:
            system_state = {
                'total_waiting': len(waiting_entries),
                'peak_hours': (9 <= datetime.now().hour <= 11) or (14 <= datetime.now().hour <= 16)
            }
            
            optimized_queue = advanced_priority_manager.optimize_queue_order(
                waiting_entries, system_state
            )
            
            if optimized_queue != waiting_entries:
                optimization_results.append({
                    'action': 'advanced_reordering',
                    'description': f'Reordered {len(waiting_entries)} queue items using advanced algorithms',
                    'impact': 'improved_efficiency'
                })
        except Exception as e:
            logger.warning(f"Advanced queue optimization failed, using traditional: {e}")
            optimized_queue = waiting_entries
        
        config = get_queue_config()
        batch_size = getattr(config, 'OPTIMIZATION_BATCH_SIZE', self.config.get('optimization_batch_size', 50))
        
        # Process entries in batches
        for i in range(0, len(optimized_queue), batch_size):
            batch = optimized_queue[i:i + batch_size]
            
            for entry in batch:
                # Recalculate priority with current wait time
                wait_time_minutes = (datetime.utcnow() - entry.created_at).total_seconds() / 60
                
                new_priority = self.priority_matrix.calculate_priority_score(
                    entry.citizen, entry.service_type, wait_time_minutes=int(wait_time_minutes)
                )
                
                # Update priority score if significantly different (using configurable threshold)
                priority_threshold = getattr(config, 'PRIORITY_UPDATE_THRESHOLD', self.config.get('priority_update_threshold', 10))
                if abs(new_priority - entry.priority_score) > priority_threshold:
                    old_priority = entry.priority_score
                    entry.priority_score = new_priority
                    optimization_results.append({
                        'queue_id': entry.id,
                        'old_priority': old_priority,
                        'new_priority': new_priority,
                        'action': 'priority_updated',
                        'threshold_used': priority_threshold
                    })
            
            # Flush batch to database
            session.flush()
        
        logger.info(f"Queue reoptimization completed. {len(optimization_results)} entries updated")
        return optimization_results
    
    def _update_queue_positions(self, optimized_queue: List[Queue]) -> int:
        """Update queue positions based on optimized order"""
        try:
            reorder_count = 0
            for index, queue_item in enumerate(optimized_queue):
                # Update position or priority score to reflect new order
                new_priority = 1000 - index  # Higher priority for earlier positions
                if queue_item.priority_score != new_priority:
                    queue_item.priority_score = new_priority
                    queue_item.updated_at = datetime.utcnow()
                    reorder_count += 1
            
            if reorder_count > 0:
                db.session.commit()
                logger.info(f"Updated positions for {reorder_count} queue items")
            
            return reorder_count
            
        except Exception as e:
            logger.error(f"Error updating queue positions: {e}")
            db.session.rollback()
            return 0
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        system_state = self.load_balancer.get_system_state()
        
        # Calculate efficiency metrics
        total_agents = Agent.query.count()
        agent_utilization = (system_state.agents_busy / total_agents * 100) if total_agents > 0 else 0
        
        # Service distribution efficiency
        service_balance = 1.0
        if system_state.service_distribution:
            values = list(system_state.service_distribution.values())
            if values:
                max_val = max(values)
                min_val = min(values)
                service_balance = (min_val / max_val) if max_val > 0 else 1.0
        
        return {
            'total_waiting': system_state.total_waiting,
            'average_wait_time': round(system_state.average_wait_time, 2),
            'agent_utilization': round(agent_utilization, 2),
            'service_balance': round(service_balance, 2),
            'peak_hours_active': system_state.peak_hours,
            'agents_available': system_state.agents_available,
            'agents_busy': system_state.agents_busy
        }