from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict

from ..models import Queue, ServiceType, Citizen, Agent, ServiceLog
from ..extensions import db

logger = logging.getLogger(__name__)

class AssignmentStrategy(Enum):
    """Different assignment strategies"""
    SPECIALIZATION_FIRST = "specialization_first"
    LOAD_BALANCED = "load_balanced"
    PERFORMANCE_BASED = "performance_based"
    HYBRID = "hybrid"

@dataclass
class AgentCapability:
    """Agent capability assessment"""
    agent_id: int
    specialization_match: float  # 0.0 to 1.0
    current_workload: float
    performance_score: float
    availability_score: float
    total_score: float

@dataclass
class AssignmentResult:
    """Result of intelligent assignment"""
    agent_id: Optional[int]
    confidence_score: float
    assignment_reason: str
    alternative_agents: List[int]
    estimated_service_time: int
    workload_impact: float

class AgentPerformanceAnalyzer:
    """Analyzes agent performance for intelligent assignment"""
    
    def __init__(self):
        self.performance_cache = {}
        self.cache_expiry = timedelta(hours=1)
    
    def get_agent_performance_score(self, agent_id: int, service_type_code: str = None) -> float:
        """Calculate agent performance score based on historical data"""
        cache_key = f"{agent_id}_{service_type_code or 'all'}"
        
        # Check cache
        if cache_key in self.performance_cache:
            cached_data, timestamp = self.performance_cache[cache_key]
            if datetime.now() - timestamp < self.cache_expiry:
                return cached_data
        
        # Calculate performance from service logs
        query = db.session.query(ServiceLog).filter_by(agent_id=agent_id)
        if service_type_code:
            query = query.join(ServiceType).filter(ServiceType.code == service_type_code)
        
        # Get recent logs (last 30 days)
        recent_logs = query.filter(
            ServiceLog.created_at >= datetime.now() - timedelta(days=30)
        ).all()
        
        if not recent_logs:
            return 0.5  # Neutral score for new agents
        
        # Calculate metrics
        total_services = len(recent_logs)
        completed_services = len([log for log in recent_logs if log.status == 'completed'])
        avg_satisfaction = sum([log.citizen_satisfaction or 3 for log in recent_logs]) / total_services
        avg_service_time = sum([log.service_duration or 10 for log in recent_logs]) / total_services
        
        # Calculate performance score (0.0 to 1.0)
        completion_rate = completed_services / total_services
        satisfaction_score = (avg_satisfaction - 1) / 4  # Normalize 1-5 to 0-1
        efficiency_score = max(0, 1 - (avg_service_time - 10) / 20)  # Penalize long service times
        
        performance_score = (completion_rate * 0.4 + satisfaction_score * 0.4 + efficiency_score * 0.2)
        
        # Cache result
        self.performance_cache[cache_key] = (performance_score, datetime.now())
        
        logger.debug(f"Agent {agent_id} performance score: {performance_score:.3f} "
                    f"(completion: {completion_rate:.2f}, satisfaction: {satisfaction_score:.2f}, "
                    f"efficiency: {efficiency_score:.2f})")
        
        return performance_score
    
    def get_agent_specialization_strength(self, agent_id: int, service_type_code: str) -> float:
        """Calculate how strong an agent's specialization is for a service type"""
        agent = db.session.get(Agent, agent_id)
        if not agent or not agent.specializations:
            return 0.0
        
        # Check for exact match first
        if service_type_code in agent.specializations:
            match_found = True
        else:
            # Check for partial matches (e.g., PASSPORT_NEW matches PASSPORT_NEW_123)
            specializations_list = agent.specializations.split(',')
            match_found = any(
                spec.strip() in service_type_code or service_type_code.startswith(spec.strip())
                for spec in specializations_list
            )
        
        if not match_found:
            return 0.0
        
        # Get performance specifically for this service type
        service_performance = self.get_agent_performance_score(agent_id, service_type_code)
        
        # Get experience (number of services completed)
        experience_count = db.session.query(ServiceLog).filter_by(agent_id=agent_id)\
            .join(ServiceType).filter(ServiceType.code == service_type_code)\
            .filter(ServiceLog.status == 'completed').count()
        
        # Experience factor (0.0 to 1.0)
        experience_factor = min(experience_count / 50, 1.0)  # Max at 50 services
        
        # Combine performance and experience
        specialization_strength = (service_performance * 0.7 + experience_factor * 0.3)
        
        return specialization_strength

class WorkloadAnalyzer:
    """Analyzes agent workload for balanced assignment"""
    
    def get_agent_current_workload(self, agent_id: int) -> float:
        """Calculate current workload score (0.0 to 1.0)"""
        # Count active and waiting queue entries
        active_count = db.session.query(Queue).filter_by(agent_id=agent_id, status='in_progress').count()
        waiting_count = db.session.query(Queue).filter_by(agent_id=agent_id, status='waiting').count()
        
        # Weight active entries more heavily
        workload_score = (active_count * 2 + waiting_count) / 10  # Normalize to 0-1 range
        
        return min(workload_score, 1.0)
    
    def get_predicted_workload(self, agent_id: int, additional_service_time: int) -> float:
        """Predict workload after adding a new service"""
        current_workload = self.get_agent_current_workload(agent_id)
        
        # Factor in the additional service time
        time_factor = additional_service_time / 60  # Convert minutes to hours
        predicted_increase = time_factor / 8  # Assume 8-hour workday
        
        return min(current_workload + predicted_increase, 1.0)
    
    def get_workload_balance_score(self, agent_ids: List[int]) -> Dict[int, float]:
        """Calculate how balanced workload distribution would be"""
        workloads = {agent_id: self.get_agent_current_workload(agent_id) 
                    for agent_id in agent_ids}
        
        if not workloads:
            return {}
        
        avg_workload = sum(workloads.values()) / len(workloads)
        
        # Calculate balance scores (higher is better)
        balance_scores = {}
        for agent_id, workload in workloads.items():
            # Agents with lower workload get higher balance scores
            balance_scores[agent_id] = max(0, 1 - abs(workload - avg_workload))
        
        return balance_scores

class IntelligentAgentAssignment:
    """Main intelligent agent assignment system"""
    
    def __init__(self):
        self.performance_analyzer = AgentPerformanceAnalyzer()
        self.workload_analyzer = WorkloadAnalyzer()
        self.assignment_history = defaultdict(list)
    
    def evaluate_agent_capability(self, agent: Agent, service_type: ServiceType, 
                                 strategy: AssignmentStrategy = AssignmentStrategy.HYBRID) -> AgentCapability:
        """Evaluate an agent's capability for a specific service"""
        
        # Specialization match
        specialization_match = self.performance_analyzer.get_agent_specialization_strength(
            agent.id, service_type.code
        )
        
        # Current workload (inverted - lower workload is better)
        current_workload = self.workload_analyzer.get_agent_current_workload(agent.id)
        workload_score = 1.0 - current_workload
        
        # Performance score
        performance_score = self.performance_analyzer.get_agent_performance_score(
            agent.id, service_type.code
        )
        
        # Availability score (based on status and recent activity)
        availability_score = self._calculate_availability_score(agent)
        
        # Calculate total score based on strategy
        if strategy == AssignmentStrategy.SPECIALIZATION_FIRST:
            total_score = (specialization_match * 0.6 + performance_score * 0.3 + 
                          workload_score * 0.1)
        elif strategy == AssignmentStrategy.LOAD_BALANCED:
            total_score = (workload_score * 0.5 + specialization_match * 0.3 + 
                          performance_score * 0.2)
        elif strategy == AssignmentStrategy.PERFORMANCE_BASED:
            total_score = (performance_score * 0.5 + specialization_match * 0.3 + 
                          workload_score * 0.2)
        else:  # HYBRID
            total_score = (specialization_match * 0.35 + performance_score * 0.35 + 
                          workload_score * 0.2 + availability_score * 0.1)
        
        return AgentCapability(
            agent_id=agent.id,
            specialization_match=specialization_match,
            current_workload=current_workload,
            performance_score=performance_score,
            availability_score=availability_score,
            total_score=total_score
        )
    
    def _calculate_availability_score(self, agent: Agent) -> float:
        """Calculate agent availability score"""
        if agent.status != 'available':
            return 0.0
        
        # Check recent login time
        if agent.login_time:
            hours_since_login = (datetime.now() - agent.login_time).total_seconds() / 3600
            if hours_since_login > 8:  # Been working too long
                return 0.3
            elif hours_since_login < 1:  # Just started
                return 0.8
            else:
                return 1.0
        
        return 0.7  # Default for agents without login time
    
    def find_best_agent(self, service_type: ServiceType, 
                       strategy: AssignmentStrategy = AssignmentStrategy.HYBRID,
                       exclude_agents: List[int] = None) -> AssignmentResult:
        """Find the best agent for a service type"""
        
        exclude_agents = exclude_agents or []
        
        # Get available agents
        available_agents = db.session.query(Agent).filter(
            Agent.status == 'available',
            Agent.is_active == True,
            ~Agent.id.in_(exclude_agents)
        ).all()
        
        if not available_agents:
            return AssignmentResult(
                agent_id=None,
                confidence_score=0.0,
                assignment_reason="No available agents",
                alternative_agents=[],
                estimated_service_time=service_type.estimated_duration,
                workload_impact=0.0
            )
        
        # Evaluate all agents
        agent_capabilities = []
        for agent in available_agents:
            try:
                capability = self.evaluate_agent_capability(agent, service_type, strategy)
                agent_capabilities.append(capability)
            except Exception as e:
                logger.error(f"Error evaluating agent {agent.id}: {str(e)}")
                # Return error result if all agents fail evaluation
                if not agent_capabilities and agent == available_agents[-1]:
                    return AssignmentResult(
                        agent_id=None,
                        confidence_score=0.0,
                        assignment_reason=f"Error during agent evaluation: {str(e)}",
                        alternative_agents=[],
                        estimated_service_time=service_type.estimated_duration,
                        workload_impact=0.0
                    )
                continue
        
        # Sort by total score (descending)
        agent_capabilities.sort(key=lambda x: x.total_score, reverse=True)
        
        best_agent = agent_capabilities[0]
        alternative_agents = [cap.agent_id for cap in agent_capabilities[1:4]]  # Top 3 alternatives
        
        # Calculate confidence score
        confidence_score = best_agent.total_score
        if len(agent_capabilities) > 1:
            # Adjust confidence based on gap to second best
            second_best_score = agent_capabilities[1].total_score
            score_gap = best_agent.total_score - second_best_score
            confidence_score = min(confidence_score + score_gap, 1.0)
        
        # Generate assignment reason
        assignment_reason = self._generate_assignment_reason(best_agent, strategy)
        
        # Calculate workload impact
        workload_impact = self.workload_analyzer.get_predicted_workload(
            best_agent.agent_id, service_type.estimated_duration
        )
        
        # Record assignment for learning
        self.assignment_history[best_agent.agent_id].append({
            'timestamp': datetime.now(),
            'service_type': service_type.code,
            'score': best_agent.total_score
        })
        
        logger.info(f"Best agent selected: {best_agent.agent_id} for {service_type.code} "
                   f"(score: {best_agent.total_score:.3f}, confidence: {confidence_score:.3f})")
        
        return AssignmentResult(
            agent_id=best_agent.agent_id,
            confidence_score=confidence_score,
            assignment_reason=assignment_reason,
            alternative_agents=alternative_agents,
            estimated_service_time=service_type.estimated_duration,
            workload_impact=workload_impact
        )
    
    def _generate_assignment_reason(self, capability: AgentCapability, 
                                   strategy: AssignmentStrategy) -> str:
        """Generate human-readable assignment reason"""
        reasons = []
        
        if capability.specialization_match > 0.7:
            reasons.append("high specialization match")
        elif capability.specialization_match > 0.3:
            reasons.append("moderate specialization")
        
        if capability.performance_score > 0.8:
            reasons.append("excellent performance history")
        elif capability.performance_score > 0.6:
            reasons.append("good performance")
        
        if capability.current_workload < 0.3:
            reasons.append("low current workload")
        elif capability.current_workload < 0.6:
            reasons.append("moderate workload")
        
        if not reasons:
            reasons.append("best available option")
        
        return f"Selected based on {', '.join(reasons)} (strategy: {strategy.value})"
    
    def get_assignment_analytics(self) -> Dict:
        """Get analytics about assignment patterns"""
        total_assignments = sum(len(history) for history in self.assignment_history.values())
        
        if total_assignments == 0:
            return {
                'total_assignments_today': 0,
                'average_assignment_time': 0,
                'strategy_usage': {},
                'agent_utilization': {}
            }
        
        # Calculate average scores by agent
        agent_avg_scores = {}
        for agent_id, history in self.assignment_history.items():
            if history:
                avg_score = sum(entry['score'] for entry in history) / len(history)
                agent_avg_scores[agent_id] = avg_score
        
        # Service type distribution
        service_distribution = defaultdict(int)
        for history in self.assignment_history.values():
            for entry in history:
                service_distribution[entry['service_type']] += 1
        
        # Strategy usage (mock data for now)
        strategy_usage = {
            'HYBRID': total_assignments * 0.6,
            'SPECIALIZATION_FIRST': total_assignments * 0.2,
            'LOAD_BALANCED': total_assignments * 0.1,
            'PERFORMANCE_BASED': total_assignments * 0.1
        }
        
        return {
            'total_assignments_today': total_assignments,
            'average_assignment_time': 5.2,  # Mock average time in minutes
            'strategy_usage': strategy_usage,
            'agent_utilization': agent_avg_scores,
            'agents_used': len(self.assignment_history),
            'service_distribution': dict(service_distribution),
            'assignment_rate': total_assignments / max(len(self.assignment_history), 1)
        }

# Global instance for use across the application
intelligent_assignment = IntelligentAgentAssignment()