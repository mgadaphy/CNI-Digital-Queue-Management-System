from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import json
from collections import defaultdict, deque
import threading
import time

from ..models import Queue, ServiceType, Citizen, Agent, ServiceLog
from ..extensions import db

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of performance metrics"""
    SYSTEM_PERFORMANCE = "system_performance"
    AGENT_PERFORMANCE = "agent_performance"
    SERVICE_EFFICIENCY = "service_efficiency"
    QUEUE_ANALYTICS = "queue_analytics"
    USER_SATISFACTION = "user_satisfaction"
    RESOURCE_UTILIZATION = "resource_utilization"
    ERROR_RATE = "error_rate"
    RESPONSE_TIME = "response_time"
    BUSINESS_METRIC = "business_metric"

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    metric_type: MetricType
    name: str
    value: float
    unit: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

@dataclass
class AuditLogEntry:
    """Audit trail entry"""
    timestamp: datetime
    event_type: str
    entity_type: str
    entity_id: Optional[int]
    user_id: Optional[int]
    action: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    level: AlertLevel
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    timestamp: datetime
    resolved: bool = False
    resolution_timestamp: Optional[datetime] = None

class RealTimeMetricsCollector:
    """Real-time metrics collection and monitoring"""
    
    def __init__(self, buffer_size: int = 1000):
        self.metrics_buffer = deque(maxlen=buffer_size)
        self.audit_buffer = deque(maxlen=buffer_size)
        self.alerts_buffer = deque(maxlen=100)
        self.active_alerts = {}
        self.metric_thresholds = self._initialize_thresholds()
        self._lock = threading.Lock()
        self.collection_interval = 30  # seconds
        self._running = False
        self._thread = None
        self._app = None
    
    def _initialize_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize performance thresholds"""
        return {
            'average_wait_time': {'warning': 15.0, 'critical': 30.0},
            'agent_utilization': {'warning': 85.0, 'critical': 95.0},
            'queue_length': {'warning': 20, 'critical': 50},
            'service_completion_rate': {'warning': 0.85, 'critical': 0.70},
            'system_response_time': {'warning': 2.0, 'critical': 5.0},
            'error_rate': {'warning': 0.05, 'critical': 0.10},
            'citizen_satisfaction': {'warning': 3.5, 'critical': 3.0}
        }
    
    def start_monitoring(self):
        """Start real-time monitoring"""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._thread.start()
            logger.info("Real-time performance monitoring started")
    
    def stop_monitoring(self):
        """Stop real-time monitoring"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Real-time performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._collect_metrics()
                self._check_alerts()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.collection_interval)
    
    def _collect_metrics(self):
        """Collect metrics from various sources"""
        try:
            if self._app:
                with self._app.app_context():
                    # System metrics
                    self._collect_system_metrics()
                    
                    # Agent metrics
                    self._collect_agent_metrics()
                    
                    # Queue metrics
                    self._collect_queue_metrics()
            else:
                logger.warning("Flask app not available for metrics collection")
            
        except Exception as e:
            logger.error(f"Error in metrics collection: {e}")
    
    def _collect_system_metrics(self):
        """Collect system-wide performance metrics"""
        try:
            # Clean up stale queue entries before calculating metrics
            self._cleanup_stale_queue_entries()
            
            # Queue metrics
            total_waiting = db.session.query(Queue).filter_by(status='waiting').count()
            total_in_progress = db.session.query(Queue).filter_by(status='in_progress').count()
            
            # Agent metrics
            total_agents = db.session.query(Agent).count()
            available_agents = db.session.query(Agent).filter_by(status='available').count()
            busy_agents = db.session.query(Agent).filter_by(status='busy').count()
            
            # Calculate wait times (only for recent entries to avoid skewed averages)
            cutoff_time = datetime.utcnow() - timedelta(hours=24)  # Only consider entries from last 24 hours
            waiting_queues = db.session.query(Queue).filter(
                Queue.status == 'waiting',
                Queue.created_at >= cutoff_time
            ).all()
            
            if waiting_queues:
                wait_times = [(datetime.utcnow() - q.created_at).total_seconds() / 60 
                             for q in waiting_queues]
                avg_wait_time = sum(wait_times) / len(wait_times)
                max_wait_time = max(wait_times)
            else:
                avg_wait_time = 0.0
                max_wait_time = 0.0
            
            # Agent utilization
            agent_utilization = (busy_agents / total_agents * 100) if total_agents > 0 else 0
            
            # Collect metrics
            timestamp = datetime.now()
            metrics = [
                PerformanceMetric(
                    MetricType.QUEUE_ANALYTICS, "total_waiting", total_waiting, "count", timestamp
                ),
                PerformanceMetric(
                    MetricType.QUEUE_ANALYTICS, "total_in_progress", total_in_progress, "count", timestamp
                ),
                PerformanceMetric(
                    MetricType.QUEUE_ANALYTICS, "average_wait_time", avg_wait_time, "minutes", timestamp,
                    threshold_warning=self.metric_thresholds['average_wait_time']['warning'],
                    threshold_critical=self.metric_thresholds['average_wait_time']['critical']
                ),
                PerformanceMetric(
                    MetricType.QUEUE_ANALYTICS, "max_wait_time", max_wait_time, "minutes", timestamp
                ),
                PerformanceMetric(
                    MetricType.RESOURCE_UTILIZATION, "agent_utilization", agent_utilization, "percentage", timestamp,
                    threshold_warning=self.metric_thresholds['agent_utilization']['warning'],
                    threshold_critical=self.metric_thresholds['agent_utilization']['critical']
                ),
                PerformanceMetric(
                    MetricType.RESOURCE_UTILIZATION, "available_agents", available_agents, "count", timestamp
                ),
                PerformanceMetric(
                    MetricType.RESOURCE_UTILIZATION, "busy_agents", busy_agents, "count", timestamp
                )
            ]
            
            with self._lock:
                self.metrics_buffer.extend(metrics)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _collect_agent_metrics(self):
        """Collect individual agent performance metrics"""
        try:
            agents = db.session.query(Agent).filter_by(is_active=True).all()
            timestamp = datetime.now()
            
            for agent in agents:
                # Current workload
                active_count = db.session.query(Queue).filter_by(
                    agent_id=agent.id, status='in_progress'
                ).count()
                waiting_count = db.session.query(Queue).filter_by(
                    agent_id=agent.id, status='waiting'
                ).count()
                
                workload = active_count + waiting_count
                
                # Recent performance (last 24 hours)
                recent_logs = db.session.query(ServiceLog).filter(
                    ServiceLog.agent_id == agent.id,
                    ServiceLog.created_at >= datetime.now() - timedelta(hours=24)
                ).all()
                
                if recent_logs:
                    completed_services = len([log for log in recent_logs if log.status == 'completed'])
                    completion_rate = completed_services / len(recent_logs)
                    avg_satisfaction = sum([log.citizen_satisfaction or 3 for log in recent_logs]) / len(recent_logs)
                    avg_service_time = sum([log.service_duration or 10 for log in recent_logs]) / len(recent_logs)
                else:
                    completion_rate = 1.0
                    avg_satisfaction = 3.0
                    avg_service_time = 10.0
                
                metrics = [
                    PerformanceMetric(
                        MetricType.AGENT_PERFORMANCE, f"agent_{agent.id}_workload", workload, "count", timestamp
                    ),
                    PerformanceMetric(
                        MetricType.AGENT_PERFORMANCE, f"agent_{agent.id}_completion_rate", completion_rate, "ratio", timestamp
                    ),
                    PerformanceMetric(
                        MetricType.AGENT_PERFORMANCE, f"agent_{agent.id}_satisfaction", avg_satisfaction, "score", timestamp
                    ),
                    PerformanceMetric(
                        MetricType.AGENT_PERFORMANCE, f"agent_{agent.id}_service_time", avg_service_time, "minutes", timestamp
                    )
                ]
                
                with self._lock:
                    self.metrics_buffer.extend(metrics)
                    
        except Exception as e:
            logger.error(f"Error collecting agent metrics: {e}")
    
    def _collect_queue_metrics(self):
        """Collect queue-specific metrics"""
        try:
            service_types = db.session.query(ServiceType).all()
            timestamp = datetime.now()
            
            for service_type in service_types:
                # Queue length by service type
                waiting_count = db.session.query(Queue).filter_by(
                    service_type_id=service_type.id, status='waiting'
                ).count()
                
                in_progress_count = db.session.query(Queue).filter_by(
                    service_type_id=service_type.id, status='in_progress'
                ).count()
                
                # Average wait time for this service type
                waiting_queues = db.session.query(Queue).filter_by(
                    service_type_id=service_type.id, status='waiting'
                ).all()
                
                if waiting_queues:
                    wait_times = [(datetime.utcnow() - q.created_at).total_seconds() / 60 
                                 for q in waiting_queues]
                    avg_wait_time = sum(wait_times) / len(wait_times)
                else:
                    avg_wait_time = 0.0
                
                metrics = [
                    PerformanceMetric(
                        MetricType.SERVICE_EFFICIENCY, f"service_{service_type.code}_waiting", 
                        waiting_count, "count", timestamp
                    ),
                    PerformanceMetric(
                        MetricType.SERVICE_EFFICIENCY, f"service_{service_type.code}_in_progress", 
                        in_progress_count, "count", timestamp
                    ),
                    PerformanceMetric(
                        MetricType.SERVICE_EFFICIENCY, f"service_{service_type.code}_wait_time", 
                        avg_wait_time, "minutes", timestamp
                    )
                ]
                
                with self._lock:
                    self.metrics_buffer.extend(metrics)
                    
        except Exception as e:
            logger.error(f"Error collecting queue metrics: {e}")
    
    def _check_alerts(self):
        """Check for performance alerts"""
        try:
            with self._lock:
                recent_metrics = list(self.metrics_buffer)[-50:]  # Check last 50 metrics
            
            for metric in recent_metrics:
                if metric.threshold_warning is None:
                    continue
                
                alert_id = f"{metric.name}_{metric.timestamp.strftime('%Y%m%d_%H%M')}"
                
                # Check for critical threshold
                if (metric.threshold_critical is not None and 
                    metric.value >= metric.threshold_critical):
                    
                    if alert_id not in self.active_alerts:
                        alert = PerformanceAlert(
                            alert_id=alert_id,
                            level=AlertLevel.CRITICAL,
                            metric_name=metric.name,
                            current_value=metric.value,
                            threshold_value=metric.threshold_critical,
                            message=f"Critical threshold exceeded for {metric.name}: {metric.value} {metric.unit}",
                            timestamp=metric.timestamp
                        )
                        self.active_alerts[alert_id] = alert
                        with self._lock:
                            self.alerts_buffer.append(alert)
                        logger.critical(alert.message)
                
                # Check for warning threshold
                elif metric.value >= metric.threshold_warning:
                    if alert_id not in self.active_alerts:
                        alert = PerformanceAlert(
                            alert_id=alert_id,
                            level=AlertLevel.WARNING,
                            metric_name=metric.name,
                            current_value=metric.value,
                            threshold_value=metric.threshold_warning,
                            message=f"Warning threshold exceeded for {metric.name}: {metric.value} {metric.unit}",
                            timestamp=metric.timestamp
                        )
                        self.active_alerts[alert_id] = alert
                        with self._lock:
                            self.alerts_buffer.append(alert)
                        logger.warning(alert.message)
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _cleanup_stale_queue_entries(self):
        """Clean up stale queue entries that have been waiting too long"""
        try:
            # Define stale threshold (entries older than 24 hours - more reasonable for testing)
            stale_threshold = datetime.utcnow() - timedelta(hours=24)
            
            # Find stale waiting entries (only unassigned ones)
            stale_entries = db.session.query(Queue).filter(
                Queue.status == 'waiting',
                Queue.agent_id.is_(None),  # Only cleanup unassigned tickets
                Queue.created_at < stale_threshold
            ).all()
            
            if stale_entries:
                logger.warning(f"Found {len(stale_entries)} stale queue entries, marking as no_show")
                
                # Mark stale entries as no_show instead of deleting them
                for entry in stale_entries:
                    entry.status = 'no_show'
                    entry.updated_at = datetime.utcnow()
                    logger.info(f"Marked queue entry {entry.ticket_number} as no_show (waited {(datetime.utcnow() - entry.created_at).total_seconds() / 3600:.1f} hours)")
                
                db.session.commit()
                logger.info(f"Successfully cleaned up {len(stale_entries)} stale queue entries")
                
        except Exception as e:
            logger.error(f"Error cleaning up stale queue entries: {e}")
            db.session.rollback()
    
    def get_current_metrics(self, metric_type: Optional[MetricType] = None, 
                           last_n_minutes: int = 5) -> List[PerformanceMetric]:
        """Get current metrics"""
        cutoff_time = datetime.now() - timedelta(minutes=last_n_minutes)
        
        with self._lock:
            metrics = [m for m in self.metrics_buffer if m.timestamp >= cutoff_time]
        
        if metric_type:
            metrics = [m for m in metrics if m.metric_type == metric_type]
        
        return sorted(metrics, key=lambda x: x.timestamp, reverse=True)
    
    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get active alerts"""
        return [alert for alert in self.active_alerts.values() if not alert.resolved]
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self.active_alerts[alert_id].resolution_timestamp = datetime.now()
            logger.info(f"Alert {alert_id} resolved")
    
    def record_metric(self, metric_type: MetricType, name: str, value: float, 
                     unit: str, metadata: Dict[str, Any] = None):
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                metric_type=metric_type,
                name=name,
                value=value,
                unit=unit,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
            with self._lock:
                self.metrics_buffer.append(metric)
                
            logger.debug(f"Recorded metric: {name} = {value} {unit}")
            
        except Exception as e:
            logger.error(f"Error recording metric {name}: {e}")

class AuditTrailManager:
    """Comprehensive audit trail management"""
    
    def __init__(self, buffer_size: int = 10000):
        self.audit_buffer = deque(maxlen=buffer_size)
        self._lock = threading.Lock()
    
    def log_event(self, event_type: str, entity_type: str, entity_id: Optional[int],
                  user_id: Optional[int], action: str, details: Dict[str, Any],
                  ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                  session_id: Optional[str] = None):
        """Log an audit event"""
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        with self._lock:
            self.audit_buffer.append(entry)
        
        # Log to file for persistence
        logger.info(f"AUDIT: {entry.event_type} - {entry.action} by user {entry.user_id} "
                   f"on {entry.entity_type} {entry.entity_id}: {json.dumps(entry.details)}")
    
    def get_audit_trail(self, entity_type: Optional[str] = None, 
                       entity_id: Optional[int] = None,
                       user_id: Optional[int] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       limit: int = 100) -> List[AuditLogEntry]:
        """Get audit trail with filters"""
        with self._lock:
            entries = list(self.audit_buffer)
        
        # Apply filters
        if entity_type:
            entries = [e for e in entries if e.entity_type == entity_type]
        if entity_id:
            entries = [e for e in entries if e.entity_id == entity_id]
        if user_id:
            entries = [e for e in entries if e.user_id == user_id]
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        
        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        return entries[:limit]

class PerformanceDashboard:
    """Performance dashboard and reporting"""
    
    def __init__(self, metrics_collector: RealTimeMetricsCollector, 
                 audit_manager: AuditTrailManager):
        self.metrics_collector = metrics_collector
        self.audit_manager = audit_manager
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        current_time = datetime.now()
        
        # Get recent metrics
        recent_metrics = self.metrics_collector.get_current_metrics(last_n_minutes=30)
        
        # Organize metrics by type
        metrics_by_type = defaultdict(list)
        for metric in recent_metrics:
            metrics_by_type[metric.metric_type.value].append({
                'name': metric.name,
                'value': metric.value,
                'unit': metric.unit,
                'timestamp': metric.timestamp.isoformat()
            })
        
        # Get active alerts
        active_alerts = self.metrics_collector.get_active_alerts()
        alerts_data = [{
            'id': alert.alert_id,
            'level': alert.level.value,
            'metric': alert.metric_name,
            'current_value': alert.current_value,
            'threshold': alert.threshold_value,
            'message': alert.message,
            'timestamp': alert.timestamp.isoformat()
        } for alert in active_alerts]
        
        # Get recent audit events
        recent_audit = self.audit_manager.get_audit_trail(
            start_time=current_time - timedelta(hours=1),
            limit=50
        )
        audit_data = [{
            'timestamp': entry.timestamp.isoformat(),
            'event_type': entry.event_type,
            'entity_type': entry.entity_type,
            'entity_id': entry.entity_id,
            'user_id': entry.user_id,
            'action': entry.action,
            'details': entry.details
        } for entry in recent_audit]
        
        # Calculate summary statistics
        system_metrics = metrics_by_type.get('system_performance', [])
        queue_metrics = metrics_by_type.get('queue_analytics', [])
        
        summary = {
            'total_metrics_collected': len(recent_metrics),
            'active_alerts_count': len(active_alerts),
            'critical_alerts_count': len([a for a in active_alerts if a.level == AlertLevel.CRITICAL]),
            'recent_audit_events': len(recent_audit),
            'monitoring_status': 'active' if self.metrics_collector._running else 'inactive'
        }
        
        return {
            'timestamp': current_time.isoformat(),
            'summary': summary,
            'metrics': dict(metrics_by_type),
            'alerts': alerts_data,
            'audit_trail': audit_data
        }
    
    def generate_performance_report(self, start_time: datetime, 
                                  end_time: datetime) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        # This would typically query a persistent storage
        # For now, we'll use the in-memory buffer
        
        all_metrics = self.metrics_collector.get_current_metrics(
            last_n_minutes=int((end_time - start_time).total_seconds() / 60)
        )
        
        # Filter by time range
        filtered_metrics = [
            m for m in all_metrics 
            if start_time <= m.timestamp <= end_time
        ]
        
        # Calculate aggregated statistics
        report = {
            'report_period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'total_metrics': len(filtered_metrics),
            'metric_types': {},
            'performance_summary': {},
            'recommendations': []
        }
        
        # Group by metric type and calculate statistics
        for metric_type in MetricType:
            type_metrics = [m for m in filtered_metrics if m.metric_type == metric_type]
            if type_metrics:
                report['metric_types'][metric_type.value] = {
                    'count': len(type_metrics),
                    'metrics': list(set([m.name for m in type_metrics]))
                }
        
        return report

# Global instances
metrics_collector = RealTimeMetricsCollector()
audit_manager = AuditTrailManager()
performance_dashboard = PerformanceDashboard(metrics_collector, audit_manager)

# Don't auto-start monitoring - wait for Flask app to be ready

logger.info("Performance monitoring system initialized")