"""
Simplified Queue Optimizer - Phase 2 Implementation

This replaces the complex HybridOptimizationEngine with a simple, reliable system
that focuses on core functionality without over-engineering.

Key Principles:
- Simple priority calculation based on service type + wait time + special needs
- Straightforward agent assignment based on availability
- Minimal database queries with proper error handling
- Clear, maintainable code without complex dependencies
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

from ..models import db, Queue, ServiceType, Citizen, Agent
from ..extensions import socketio

logger = logging.getLogger(__name__)

@dataclass
class SimpleOptimizationResult:
    """Simple result structure for queue optimization"""
    success: bool
    message: str
    optimized_count: int
    total_tickets: int
    details: Optional[Dict] = None

class SimplePriorityCalculator:
    """Simplified priority calculation system"""
    
    # Base priority scores by service type
    SERVICE_PRIORITIES = {
        'EMERGENCY': 1000,      # Highest priority
        'APPOINTMENT': 800,     # Pre-scheduled appointments
        'COLLECTION': 600,      # Document collection
        'RENEWAL': 400,         # Renewals
        'CORRECTION': 300,      # Corrections
        'NEW_APPLICATION': 200  # New applications
    }
    
    # Wait time bonus: 2 points per minute waiting (max 200 points)
    WAIT_TIME_MULTIPLIER = 2
    MAX_WAIT_BONUS = 200
    
    # Special needs bonuses
    SPECIAL_NEEDS_BONUS = {
        'elderly': 100,
        'disability': 150,
        'pregnant': 120,
        'appointment': 300
    }
    
    def calculate_priority_score(self, citizen: Citizen, service_type: ServiceType, 
                               wait_time_minutes: int = 0, special_factors: Dict = None) -> float:
        """
        Calculate priority score using simple, reliable formula:
        Priority = Base Service Priority + Wait Time Bonus + Special Needs Bonus
        """
        try:
            # Base priority from service type
            base_priority = self.SERVICE_PRIORITIES.get(service_type.code, 100)
            
            # Wait time bonus (capped at maximum)
            wait_bonus = min(wait_time_minutes * self.WAIT_TIME_MULTIPLIER, self.MAX_WAIT_BONUS)
            
            # Special needs bonus
            special_bonus = 0
            if special_factors:
                for factor, bonus in self.SPECIAL_NEEDS_BONUS.items():
                    if special_factors.get(factor, False):
                        special_bonus += bonus
            
            # Calculate total score
            total_score = base_priority + wait_bonus + special_bonus
            
            logger.debug(f"Priority calculation for citizen {citizen.id}: "
                        f"base={base_priority}, wait={wait_bonus}, "
                        f"special={special_bonus}, total={total_score}")
            
            return float(total_score)
            
        except Exception as e:
            logger.error(f"Error calculating priority for citizen {citizen.id}: {e}")
            # Return default priority based on service type
            return float(self.SERVICE_PRIORITIES.get(service_type.code, 100))

class SimpleAgentAssigner:
    """Simplified agent assignment system"""
    
    def find_best_available_agent(self, service_type: ServiceType) -> Optional[Agent]:
        """
        Find the best available agent using simple criteria:
        1. Agent must be available
        2. Prefer agents with fewer current assignments
        3. Simple round-robin if multiple agents have same workload
        """
        try:
            # Get all available agents
            available_agents = Agent.query.filter_by(status='available').all()
            
            if not available_agents:
                logger.info("No available agents found")
                return None
            
            # If only one agent, return it
            if len(available_agents) == 1:
                return available_agents[0]
            
            # Find agent with lowest workload
            best_agent = None
            lowest_workload = float('inf')
            
            for agent in available_agents:
                # Count current assignments
                current_workload = Queue.query.filter_by(
                    agent_id=agent.id,
                    status='in_progress'
                ).count()
                
                if current_workload < lowest_workload:
                    lowest_workload = current_workload
                    best_agent = agent
            
            logger.info(f"Selected agent {best_agent.id} with workload {lowest_workload}")
            return best_agent
            
        except Exception as e:
            logger.error(f"Error finding available agent: {e}")
            return None

class SimpleQueueOptimizer:
    """
    Simplified queue optimizer that replaces the complex HybridOptimizationEngine
    
    This system focuses on:
    - Reliable priority calculation
    - Simple agent assignment
    - Minimal database queries
    - Clear error handling
    """
    
    def __init__(self):
        self.priority_calculator = SimplePriorityCalculator()
        self.agent_assigner = SimpleAgentAssigner()
    
    def optimize_queue(self, max_tickets: int = 100) -> SimpleOptimizationResult:
        """
        Optimize the queue by recalculating priorities for waiting tickets
        
        Args:
            max_tickets: Maximum number of tickets to process (prevents performance issues)
            
        Returns:
            SimpleOptimizationResult with success status and details
        """
        try:
            logger.info("Starting simple queue optimization")
            
            # Get waiting tickets (limit to prevent performance issues)
            waiting_tickets = Queue.query.filter_by(status='waiting').limit(max_tickets).all()
            
            if not waiting_tickets:
                return SimpleOptimizationResult(
                    success=True,
                    message="No tickets in queue to optimize",
                    optimized_count=0,
                    total_tickets=0
                )
            
            optimized_count = 0
            errors = []
            
            for ticket in waiting_tickets:
                try:
                    # Calculate wait time
                    wait_time_minutes = int(
                        (datetime.utcnow() - ticket.created_at).total_seconds() / 60
                    ) if ticket.created_at else 0
                    
                    # Get special factors
                    special_factors = self._get_special_factors(ticket.citizen)
                    
                    # Calculate new priority
                    new_priority = self.priority_calculator.calculate_priority_score(
                        ticket.citizen,
                        ticket.service_type,
                        wait_time_minutes,
                        special_factors
                    )
                    
                    # Update if priority changed significantly (>5 points difference)
                    if abs((ticket.priority_score or 0) - new_priority) > 5:
                        old_priority = ticket.priority_score
                        ticket.priority_score = new_priority
                        ticket.updated_at = datetime.utcnow()
                        optimized_count += 1
                        
                        logger.debug(f"Updated ticket {ticket.id} priority: {old_priority} -> {new_priority}")
                    
                except Exception as e:
                    error_msg = f"Error optimizing ticket {ticket.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue
            
            # Commit changes
            db.session.commit()
            
            # Prepare result
            result = SimpleOptimizationResult(
                success=True,
                message=f"Queue optimized successfully. {optimized_count} tickets updated.",
                optimized_count=optimized_count,
                total_tickets=len(waiting_tickets),
                details={
                    'errors': errors if errors else None,
                    'optimization_time': datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"Queue optimization completed: {optimized_count}/{len(waiting_tickets)} tickets updated")
            return result
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Queue optimization failed: {str(e)}"
            logger.error(error_msg)
            
            return SimpleOptimizationResult(
                success=False,
                message=error_msg,
                optimized_count=0,
                total_tickets=0,
                details={'error': str(e)}
            )
    
    def assign_agent_to_ticket(self, ticket: Queue) -> bool:
        """
        Assign an available agent to a ticket
        
        Args:
            ticket: Queue ticket to assign agent to
            
        Returns:
            bool: True if agent assigned successfully, False otherwise
        """
        try:
            if ticket.agent_id:
                logger.info(f"Ticket {ticket.id} already has agent {ticket.agent_id}")
                return True
            
            # Find best available agent
            agent = self.agent_assigner.find_best_available_agent(ticket.service_type)
            
            if not agent:
                logger.info(f"No available agent for ticket {ticket.id}")
                return False
            
            # Assign agent to ticket
            ticket.agent_id = agent.id
            ticket.updated_at = datetime.utcnow()
            
            # Update agent status
            agent.status = 'busy'
            
            db.session.commit()
            
            logger.info(f"Assigned agent {agent.id} to ticket {ticket.id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error assigning agent to ticket {ticket.id}: {e}")
            return False
    
    def _get_special_factors(self, citizen: Citizen) -> Dict[str, bool]:
        """Extract special factors from citizen data"""
        special_factors = {}
        
        try:
            # Check special_needs field for factors
            if citizen.special_needs:
                special_needs_lower = citizen.special_needs.lower()
                
                if 'elderly' in special_needs_lower:
                    special_factors['elderly'] = True
                
                if 'disability' in special_needs_lower:
                    special_factors['disability'] = True
                
                if 'pregnant' in special_needs_lower:
                    special_factors['pregnant'] = True
                
                if 'appointment' in special_needs_lower:
                    special_factors['appointment'] = True
            
            # Also check for individual attributes if they exist (backward compatibility)
            if hasattr(citizen, 'is_elderly') and citizen.is_elderly:
                special_factors['elderly'] = True
            
            if hasattr(citizen, 'has_disability') and citizen.has_disability:
                special_factors['disability'] = True
            
            if hasattr(citizen, 'is_pregnant') and citizen.is_pregnant:
                special_factors['pregnant'] = True
            
            if hasattr(citizen, 'appointment_time') and citizen.appointment_time:
                special_factors['appointment'] = True
                
        except Exception as e:
            logger.warning(f"Error extracting special factors for citizen {citizen.id}: {e}")
        
        return special_factors
    
    def get_queue_statistics(self) -> Dict:
        """Get simple queue statistics"""
        try:
            stats = {
                'waiting': Queue.query.filter_by(status='waiting').count(),
                'in_progress': Queue.query.filter_by(status='in_progress').count(),
                'completed_today': Queue.query.filter(
                    Queue.status == 'completed',
                    Queue.updated_at >= datetime.utcnow().date()
                ).count(),
                'available_agents': Agent.query.filter_by(status='available').count(),
                'busy_agents': Agent.query.filter_by(status='busy').count(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue statistics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

# Global instance for easy import
simple_optimizer = SimpleQueueOptimizer()
