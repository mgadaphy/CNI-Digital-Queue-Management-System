import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from flask import current_app

from ..models import Queue, Agent, db
from ..extensions import socketio
from .hybrid_optimizer import HybridOptimizationEngine
from .queue_config import get_queue_config
from ..utils.websocket_utils import emit_queue_update, emit_metrics_update

logger = logging.getLogger(__name__)

class QueueOptimizationScheduler:
    """Background scheduler for periodic queue optimization tasks"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.config = get_queue_config()
        self.optimizer = HybridOptimizationEngine()
        self.is_running = False
        self.job_stats = {
            'periodic_optimizations': 0,
            'reoptimizations': 0,
            'failed_jobs': 0,
            'last_optimization': None,
            'last_reoptimization': None
        }
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed_listener, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener, EVENT_JOB_ERROR)
    
    def start(self) -> None:
        """Start the scheduler with configured jobs"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Add periodic optimization job
            self.scheduler.add_job(
                func=self._periodic_optimization_job,
                trigger=IntervalTrigger(minutes=self.config.PERIODIC_OPTIMIZATION_INTERVAL),
                id='periodic_optimization',
                name='Periodic Queue Optimization',
                replace_existing=True,
                max_instances=1
            )
            
            # Add reoptimization job
            self.scheduler.add_job(
                func=self._reoptimization_job,
                trigger=IntervalTrigger(minutes=self.config.REOPTIMIZATION_INTERVAL),
                id='queue_reoptimization',
                name='Queue Reoptimization',
                replace_existing=True,
                max_instances=1
            )
            
            # Add metrics collection job
            if self.config.PERFORMANCE_METRICS_ENABLED:
                self.scheduler.add_job(
                    func=self._metrics_collection_job,
                    trigger=IntervalTrigger(seconds=self.config.METRICS_COLLECTION_INTERVAL),
                    id='metrics_collection',
                    name='Metrics Collection',
                    replace_existing=True,
                    max_instances=1
                )
            
            # Add daily cleanup job (runs at 2 AM)
            self.scheduler.add_job(
                func=self._daily_cleanup_job,
                trigger=CronTrigger(hour=2, minute=0),
                name='Daily Queue Cleanup',
                replace_existing=True
            )
            
            # Start the scheduler (disabled for SQLite compatibility)
            # self.scheduler.start()
            logger.info("Queue optimization scheduler disabled for SQLite compatibility")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise
    def stop(self) -> None:
        """Stop the scheduler"""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Queue optimization scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")
    
    def _periodic_optimization_job(self) -> None:
        """Periodic optimization job"""
        try:
            logger.info("Starting periodic queue optimization")
            
            # Get waiting queue entries
            waiting_entries = Queue.query.filter_by(status='waiting').all()
            
            if not waiting_entries:
                logger.info("No waiting entries to optimize")
                return
            
            # Perform optimization
            optimization_results = self.optimizer.optimize_queue(waiting_entries)
            
            # Update job statistics
            self.job_stats['periodic_optimizations'] += 1
            self.job_stats['last_optimization'] = datetime.utcnow()
            
            # Emit update notification
            emit_queue_update(
                f"Periodic optimization completed for {len(waiting_entries)} entries",
                update_type='optimization',
                data={
                    'optimization_type': 'periodic',
                    'entries_processed': len(waiting_entries),
                    'results': optimization_results[:5]  # Limit to first 5 results
                }
            )
            
            logger.info(f"Periodic optimization completed. Processed {len(waiting_entries)} entries")
            
        except Exception as e:
            logger.error(f"Error in periodic optimization job: {str(e)}")
            self.job_stats['failed_jobs'] += 1
    
    def _reoptimization_job(self) -> None:
        """Full queue reoptimization job"""
        try:
            logger.info("Starting queue reoptimization")
            
            # Perform full reoptimization
            optimization_results = self.optimizer.reoptimize_queue()
            
            # Update job statistics
            self.job_stats['reoptimizations'] += 1
            self.job_stats['last_reoptimization'] = datetime.utcnow()
            
            # Emit update notification
            emit_queue_update(
                f"Queue reoptimization completed with {len(optimization_results)} changes",
                update_type='reoptimization',
                data={
                    'optimization_type': 'full_reoptimization',
                    'changes_made': len(optimization_results),
                    'results': optimization_results[:10]  # Limit to first 10 results
                }
            )
            
            logger.info(f"Queue reoptimization completed. Made {len(optimization_results)} changes")
            
        except Exception as e:
            logger.error(f"Error in reoptimization job: {str(e)}")
            self.job_stats['failed_jobs'] += 1
    
    def _metrics_collection_job(self) -> None:
        """Metrics collection job"""
        try:
            # Collect current metrics
            metrics = self.optimizer.get_performance_metrics()
            
            # Add scheduler statistics
            metrics['scheduler_stats'] = self.job_stats.copy()
            
            # Emit metrics update
            emit_metrics_update({
                'performance_metrics': metrics,
                'collection_time': datetime.utcnow().isoformat(),
                'update_type': 'scheduled_collection'
            })
            
        except Exception as e:
            logger.error(f"Error in metrics collection job: {str(e)}")
    
    def _daily_cleanup_job(self) -> None:
        """Daily cleanup job for old completed entries"""
        try:
            logger.info("Starting daily queue cleanup")
            
            # Remove completed entries older than 7 days
            cutoff_date = datetime.utcnow() - timedelta(days=7)
            old_entries = Queue.query.filter(
                Queue.status == 'completed',
                Queue.updated_at < cutoff_date
            ).all()
            
            if old_entries:
                for entry in old_entries:
                    db.session.delete(entry)
                
                db.session.commit()
                logger.info(f"Cleaned up {len(old_entries)} old completed entries")
                
                # Emit cleanup notification
                emit_queue_update(
                    f"Daily cleanup completed: removed {len(old_entries)} old entries",
                    update_type='cleanup',
                    data={
                        'cleanup_type': 'daily',
                        'entries_removed': len(old_entries),
                        'cutoff_date': cutoff_date.isoformat()
                    }
                )
            else:
                logger.info("No old entries to clean up")
            
        except Exception as e:
            logger.error(f"Error in daily cleanup job: {str(e)}")
            db.session.rollback()
    
    def _job_executed_listener(self, event) -> None:
        """Listener for successful job execution"""
        logger.debug(f"Job {event.job_id} executed successfully")
    
    def _job_error_listener(self, event) -> None:
        """Listener for job execution errors"""
        logger.error(f"Job {event.job_id} failed: {event.exception}")
        self.job_stats['failed_jobs'] += 1
        
        # Emit error notification
        emit_queue_update(
            f"Scheduled job {event.job_id} failed",
            update_type='error',
            data={
                'job_id': event.job_id,
                'error': str(event.exception),
                'timestamp': datetime.utcnow().isoformat()
            }
        )
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get current job status and statistics"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        
        return {
            'is_running': self.is_running,
            'jobs': jobs,
            'statistics': self.job_stats.copy()
        }
    
    def trigger_optimization_now(self) -> Dict[str, Any]:
        """Manually trigger optimization"""
        try:
            self._periodic_optimization_job()
            return {
                'success': True,
                'message': 'Manual optimization triggered successfully',
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Manual optimization trigger failed: {str(e)}")
            return {
                'success': False,
                'message': f'Manual optimization failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def trigger_reoptimization_now(self) -> Dict[str, Any]:
        """Manually trigger full reoptimization"""
        try:
            self._reoptimization_job()
            return {
                'success': True,
                'message': 'Manual reoptimization triggered successfully',
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Manual reoptimization trigger failed: {str(e)}")
            return {
                'success': False,
                'message': f'Manual reoptimization failed: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def update_job_intervals(self, periodic_interval: Optional[int] = None, 
                           reoptimization_interval: Optional[int] = None) -> None:
        """Update job intervals dynamically"""
        try:
            if periodic_interval:
                self.scheduler.modify_job(
                    'periodic_optimization',
                    trigger=IntervalTrigger(minutes=periodic_interval)
                )
                logger.info(f"Updated periodic optimization interval to {periodic_interval} minutes")
            
            if reoptimization_interval:
                self.scheduler.modify_job(
                    'queue_reoptimization',
                    trigger=IntervalTrigger(minutes=reoptimization_interval)
                )
                logger.info(f"Updated reoptimization interval to {reoptimization_interval} minutes")
                
        except Exception as e:
            logger.error(f"Error updating job intervals: {str(e)}")

# Global scheduler instance
queue_scheduler = QueueOptimizationScheduler()

def get_queue_scheduler() -> QueueOptimizationScheduler:
    """Get the global queue scheduler instance"""
    return queue_scheduler

def start_queue_scheduler() -> None:
    """Start the queue scheduler"""
    queue_scheduler.start()

def stop_queue_scheduler() -> None:
    """Stop the queue scheduler"""
    queue_scheduler.stop()