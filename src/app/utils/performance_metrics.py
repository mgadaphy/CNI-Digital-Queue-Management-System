from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import time
import threading
from ..models import Queue, Agent, ServiceType
from ..extensions import db
from .queue_logger import get_queue_logger
from .config_manager import get_queue_optimization_config

@dataclass
class PerformanceMetric:
    """Individual performance metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    category: str
    metadata: Dict[str, Any] = None

@dataclass
class QueuePerformanceSnapshot:
    """Snapshot of queue performance at a point in time"""
    timestamp: datetime
    total_queue_length: int
    average_wait_time: float
    service_efficiency: float
    agent_utilization: float
    optimization_score: float
    active_agents: int
    completed_services: int
    priority_distribution: Dict[str, int]

class PerformanceMetricsCollector:
    """Collects and analyzes queue optimization performance metrics"""
    
    def __init__(self, max_history_size: int = 1000):
        self.metrics_history = deque(maxlen=max_history_size)
        self.snapshots_history = deque(maxlen=max_history_size)
        self.real_time_metrics = defaultdict(list)
        self.optimization_metrics = defaultdict(list)
        self.lock = threading.Lock()
        self.start_time = datetime.now()
        
    def record_metric(self, name: str, value: float, category: str = 'general', 
                     metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        with self.lock:
            metric = PerformanceMetric(
                timestamp=datetime.now(),
                metric_name=name,
                value=value,
                category=category,
                metadata=metadata or {}
            )
            self.metrics_history.append(metric)
            self.real_time_metrics[name].append((datetime.now(), value))
            
            # Keep only recent real-time metrics (last hour)
            cutoff_time = datetime.now() - timedelta(hours=1)
            self.real_time_metrics[name] = [
                (ts, val) for ts, val in self.real_time_metrics[name] 
                if ts > cutoff_time
            ]
    
    def record_optimization_result(self, optimization_time: float, changes_made: int, 
                                 efficiency_improvement: float, algorithm_used: str,
                                 queue_size_before: int, queue_size_after: int):
        """Record optimization operation results"""
        timestamp = datetime.now()
        
        # Record individual metrics
        self.record_metric('optimization_time', optimization_time, 'optimization')
        self.record_metric('optimization_changes', changes_made, 'optimization')
        self.record_metric('efficiency_improvement', efficiency_improvement, 'optimization')
        self.record_metric('queue_size_reduction', queue_size_before - queue_size_after, 'optimization')
        
        # Store comprehensive optimization data
        optimization_data = {
            'timestamp': timestamp,
            'optimization_time': optimization_time,
            'changes_made': changes_made,
            'efficiency_improvement': efficiency_improvement,
            'algorithm_used': algorithm_used,
            'queue_size_before': queue_size_before,
            'queue_size_after': queue_size_after,
            'success_rate': 1.0 if changes_made > 0 else 0.0
        }
        
        with self.lock:
            self.optimization_metrics['results'].append(optimization_data)
    
    def take_queue_snapshot(self) -> QueuePerformanceSnapshot:
        """Take a comprehensive snapshot of current queue performance"""
        try:
            from sqlalchemy import func
            
            # Get current queue statistics
            current_time = datetime.now()
            
            # Total queue length
            total_queue = db.session.query(QueueEntry).filter(
                QueueEntry.status == 'waiting'
            ).count()
            
            # Average wait time for waiting entries
            waiting_entries = db.session.query(QueueEntry).filter(
                QueueEntry.status == 'waiting'
            ).all()
            
            if waiting_entries:
                wait_times = [
                    (current_time - entry.created_at).total_seconds() / 60 
                    for entry in waiting_entries
                ]
                avg_wait_time = statistics.mean(wait_times)
            else:
                avg_wait_time = 0.0
            
            # Agent utilization
            total_agents = db.session.query(Agent).filter(
                Agent.status.in_(['available', 'busy'])
            ).count()
            
            busy_agents = db.session.query(Agent).filter(
                Agent.status == 'busy'
            ).count()
            
            agent_utilization = (busy_agents / total_agents * 100) if total_agents > 0 else 0.0
            
            # Service efficiency (completed services in last hour)
            hour_ago = current_time - timedelta(hours=1)
            completed_services = db.session.query(QueueEntry).filter(
                QueueEntry.status == 'completed',
                QueueEntry.updated_at >= hour_ago
            ).count()
            
            service_efficiency = completed_services / max(total_agents, 1)
            
            # Priority distribution
            priority_dist = db.session.query(
                QueueEntry.priority_score,
                func.count(QueueEntry.id)
            ).filter(
                QueueEntry.status == 'waiting'
            ).group_by(QueueEntry.priority_score).all()
            
            priority_distribution = {
                'high': sum(count for score, count in priority_dist if score > 100),
                'medium': sum(count for score, count in priority_dist if 50 <= score <= 100),
                'low': sum(count for score, count in priority_dist if score < 50)
            }
            
            # Calculate optimization score based on multiple factors
            optimization_score = self._calculate_optimization_score(
                avg_wait_time, agent_utilization, service_efficiency, total_queue
            )
            
            snapshot = QueuePerformanceSnapshot(
                timestamp=current_time,
                total_queue_length=total_queue,
                average_wait_time=avg_wait_time,
                service_efficiency=service_efficiency,
                agent_utilization=agent_utilization,
                optimization_score=optimization_score,
                active_agents=total_agents,
                completed_services=completed_services,
                priority_distribution=priority_distribution
            )
            
            with self.lock:
                self.snapshots_history.append(snapshot)
            
            return snapshot
            
        except Exception as e:
            queue_logger = get_queue_logger()
            queue_logger.log_error(e, {'operation': 'take_queue_snapshot'})
            
            # Return empty snapshot on error
            return QueuePerformanceSnapshot(
                timestamp=current_time,
                total_queue_length=0,
                average_wait_time=0.0,
                service_efficiency=0.0,
                agent_utilization=0.0,
                optimization_score=0.0,
                active_agents=0,
                completed_services=0,
                priority_distribution={'high': 0, 'medium': 0, 'low': 0}
            )
    
    def _calculate_optimization_score(self, avg_wait_time: float, agent_utilization: float,
                                    service_efficiency: float, queue_length: int) -> float:
        """Calculate overall optimization score (0-100)"""
        config = get_queue_optimization_config()
        
        # Normalize metrics to 0-100 scale
        wait_time_score = max(0, 100 - (avg_wait_time / config.max_wait_time_minutes * 100))
        utilization_score = min(agent_utilization, 100)  # Cap at 100%
        efficiency_score = min(service_efficiency * 10, 100)  # Scale efficiency
        queue_score = max(0, 100 - (queue_length / 100 * 100))  # Penalize long queues
        
        # Weighted average
        optimization_score = (
            wait_time_score * 0.3 +
            utilization_score * 0.25 +
            efficiency_score * 0.25 +
            queue_score * 0.2
        )
        
        return round(optimization_score, 2)
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            # Filter metrics by time period
            recent_metrics = [
                metric for metric in self.metrics_history 
                if metric.timestamp > cutoff_time
            ]
            
            recent_snapshots = [
                snapshot for snapshot in self.snapshots_history 
                if snapshot.timestamp > cutoff_time
            ]
        
        if not recent_metrics and not recent_snapshots:
            return {'message': 'No performance data available for the specified period'}
        
        # Aggregate metrics by category
        metrics_by_category = defaultdict(list)
        for metric in recent_metrics:
            metrics_by_category[metric.category].append(metric.value)
        
        # Calculate statistics
        summary = {
            'time_period_hours': hours,
            'total_metrics_collected': len(recent_metrics),
            'total_snapshots': len(recent_snapshots),
            'categories': {}
        }
        
        for category, values in metrics_by_category.items():
            if values:
                summary['categories'][category] = {
                    'count': len(values),
                    'average': round(statistics.mean(values), 2),
                    'min': round(min(values), 2),
                    'max': round(max(values), 2),
                    'median': round(statistics.median(values), 2)
                }
        
        # Add snapshot-based insights
        if recent_snapshots:
            latest_snapshot = recent_snapshots[-1]
            summary['current_state'] = asdict(latest_snapshot)
            
            # Trend analysis
            if len(recent_snapshots) > 1:
                first_snapshot = recent_snapshots[0]
                summary['trends'] = {
                    'queue_length_change': latest_snapshot.total_queue_length - first_snapshot.total_queue_length,
                    'wait_time_change': round(latest_snapshot.average_wait_time - first_snapshot.average_wait_time, 2),
                    'efficiency_change': round(latest_snapshot.service_efficiency - first_snapshot.service_efficiency, 2),
                    'optimization_score_change': round(latest_snapshot.optimization_score - first_snapshot.optimization_score, 2)
                }
        
        return summary
    
    def get_optimization_analytics(self) -> Dict[str, Any]:
        """Get detailed optimization performance analytics"""
        with self.lock:
            optimization_results = self.optimization_metrics.get('results', [])
        
        if not optimization_results:
            return {'message': 'No optimization data available'}
        
        # Calculate optimization statistics
        optimization_times = [result['optimization_time'] for result in optimization_results]
        changes_made = [result['changes_made'] for result in optimization_results]
        efficiency_improvements = [result['efficiency_improvement'] for result in optimization_results]
        success_rates = [result['success_rate'] for result in optimization_results]
        
        analytics = {
            'total_optimizations': len(optimization_results),
            'average_optimization_time': round(statistics.mean(optimization_times), 3),
            'average_changes_per_optimization': round(statistics.mean(changes_made), 1),
            'average_efficiency_improvement': round(statistics.mean(efficiency_improvements), 2),
            'optimization_success_rate': round(statistics.mean(success_rates) * 100, 1),
            'performance_trends': {
                'optimization_time': {
                    'min': round(min(optimization_times), 3),
                    'max': round(max(optimization_times), 3),
                    'median': round(statistics.median(optimization_times), 3)
                },
                'efficiency_improvement': {
                    'min': round(min(efficiency_improvements), 2),
                    'max': round(max(efficiency_improvements), 2),
                    'median': round(statistics.median(efficiency_improvements), 2)
                }
            },
            'algorithm_usage': {}
        }
        
        # Algorithm usage statistics
        algorithm_counts = defaultdict(int)
        for result in optimization_results:
            algorithm_counts[result['algorithm_used']] += 1
        
        total_optimizations = len(optimization_results)
        for algorithm, count in algorithm_counts.items():
            analytics['algorithm_usage'][algorithm] = {
                'count': count,
                'percentage': round((count / total_optimizations) * 100, 1)
            }
        
        return analytics
    
    def get_real_time_metrics(self, metric_names: List[str] = None) -> Dict[str, List]:
        """Get real-time metrics for specified metric names"""
        with self.lock:
            if metric_names:
                return {name: self.real_time_metrics.get(name, []) for name in metric_names}
            else:
                return dict(self.real_time_metrics)
    
    def clear_old_data(self, hours: int = 168):  # Default: 1 week
        """Clear performance data older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self.lock:
            # Clear old metrics
            self.metrics_history = deque(
                [metric for metric in self.metrics_history if metric.timestamp > cutoff_time],
                maxlen=self.metrics_history.maxlen
            )
            
            # Clear old snapshots
            self.snapshots_history = deque(
                [snapshot for snapshot in self.snapshots_history if snapshot.timestamp > cutoff_time],
                maxlen=self.snapshots_history.maxlen
            )
            
            # Clear old real-time metrics
            for metric_name in list(self.real_time_metrics.keys()):
                self.real_time_metrics[metric_name] = [
                    (ts, val) for ts, val in self.real_time_metrics[metric_name]
                    if ts > cutoff_time
                ]
                
                # Remove empty metric lists
                if not self.real_time_metrics[metric_name]:
                    del self.real_time_metrics[metric_name]
            
            # Clear old optimization metrics
            self.optimization_metrics['results'] = [
                result for result in self.optimization_metrics.get('results', [])
                if result['timestamp'] > cutoff_time
            ]

# Global instance
_performance_collector = None

def get_performance_collector() -> PerformanceMetricsCollector:
    """Get the global performance metrics collector instance"""
    global _performance_collector
    if _performance_collector is None:
        _performance_collector = PerformanceMetricsCollector()
    return _performance_collector

def record_performance_metric(name: str, value: float, category: str = 'general', 
                            metadata: Dict[str, Any] = None):
    """Convenience function to record a performance metric"""
    collector = get_performance_collector()
    collector.record_metric(name, value, category, metadata)

def take_performance_snapshot() -> QueuePerformanceSnapshot:
    """Convenience function to take a performance snapshot"""
    collector = get_performance_collector()
    return collector.take_queue_snapshot()