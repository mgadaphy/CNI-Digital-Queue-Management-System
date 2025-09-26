import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Type, Union
from functools import wraps
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy import event, text
from sqlalchemy.exc import (
    SQLAlchemyError, 
    IntegrityError, 
    OperationalError, 
    DisconnectionError,
    TimeoutError as SQLTimeoutError
)
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from ..extensions import db
from ..queue_logic.queue_config import get_queue_config

logger = logging.getLogger(__name__)

class DatabaseTransactionManager:
    """Enhanced database transaction manager with optimization and error handling"""
    
    def __init__(self):
        self.config = get_queue_config()
        self.transaction_stats = {
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'rollback_count': 0,
            'retry_count': 0,
            'average_duration': 0.0,
            'last_reset': datetime.utcnow()
        }
        self.active_transactions = {}
        self._setup_connection_events()
    
    def _setup_connection_events(self):
        """Setup SQLAlchemy connection event listeners for monitoring"""
        
        @event.listens_for(db.engine, 'connect')
        def set_connection_options(dbapi_connection, connection_record):
            """Set connection-level options for optimization"""
            try:
                # Set connection timeout
                if hasattr(dbapi_connection, 'execute'):
                    # For SQLite
                    dbapi_connection.execute(f"PRAGMA busy_timeout = {self.config.DB_TRANSACTION_TIMEOUT * 1000}")
                    dbapi_connection.execute("PRAGMA journal_mode = WAL")
                    dbapi_connection.execute("PRAGMA synchronous = NORMAL")
                    dbapi_connection.execute("PRAGMA cache_size = -64000")  # 64MB cache
                    
            except Exception as e:
                logger.warning(f"Could not set connection options: {str(e)}")
        
        @event.listens_for(db.engine, 'checkout')
        def checkout_listener(dbapi_connection, connection_record, connection_proxy):
            """Monitor connection checkout"""
            connection_record.checkout_time = time.time()
        
        @event.listens_for(db.engine, 'checkin')
        def checkin_listener(dbapi_connection, connection_record):
            """Monitor connection checkin and cleanup"""
            if hasattr(connection_record, 'checkout_time'):
                duration = time.time() - connection_record.checkout_time
                if duration > 30:  # Log long-running connections
                    logger.warning(f"Long-running database connection: {duration:.2f}s")
    
    @contextmanager
    def transaction(self, isolation_level: Optional[str] = None, 
                   timeout: Optional[int] = None, 
                   retry_on_failure: bool = True):
        """Enhanced transaction context manager with retry and rollback handling"""
        
        transaction_id = f"txn_{int(time.time() * 1000000)}"
        start_time = time.time()
        timeout = timeout or self.config.DB_TRANSACTION_TIMEOUT
        
        self.transaction_stats['total_transactions'] += 1
        self.active_transactions[transaction_id] = {
            'start_time': start_time,
            'timeout': timeout,
            'isolation_level': isolation_level
        }
        
        session = None
        retry_count = 0
        max_retries = self.config.DB_RETRY_ATTEMPTS if retry_on_failure else 0
        
        while retry_count <= max_retries:
            try:
                # Create new session for this transaction
                session = db.session
                
                # Set isolation level if specified (MySQL specific - skip for SQLite)
                if isolation_level and 'mysql' in str(session.bind.dialect):
                    session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
                
                # Set transaction timeout (MySQL specific - skip for SQLite)
                if 'mysql' in str(session.bind.dialect):
                    session.execute(text(f"SET SESSION innodb_lock_wait_timeout = {timeout}"))
                
                logger.debug(f"Starting transaction {transaction_id} (attempt {retry_count + 1})")
                
                yield session
                
                # Commit the transaction
                session.commit()
                
                # Update statistics
                duration = time.time() - start_time
                self._update_success_stats(duration)
                
                logger.debug(f"Transaction {transaction_id} committed successfully in {duration:.3f}s")
                break
                
            except (OperationalError, DisconnectionError, SQLTimeoutError) as e:
                # Retryable errors
                retry_count += 1
                self.transaction_stats['retry_count'] += 1
                
                if session:
                    try:
                        session.rollback()
                        self.transaction_stats['rollback_count'] += 1
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
                
                if retry_count <= max_retries:
                    wait_time = min(2 ** retry_count, 10)  # Exponential backoff, max 10s
                    logger.warning(
                        f"Transaction {transaction_id} failed (attempt {retry_count}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Transaction {transaction_id} failed after {max_retries} retries: {str(e)}")
                    self._update_failure_stats()
                    raise
            
            except IntegrityError as e:
                # Non-retryable integrity errors
                if session:
                    try:
                        session.rollback()
                        self.transaction_stats['rollback_count'] += 1
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
                
                logger.error(f"Transaction {transaction_id} integrity error: {str(e)}")
                self._update_failure_stats()
                raise
            
            except Exception as e:
                # Other database errors
                if session:
                    try:
                        session.rollback()
                        self.transaction_stats['rollback_count'] += 1
                    except Exception as rollback_error:
                        logger.error(f"Error during rollback: {str(rollback_error)}")
                
                logger.error(f"Transaction {transaction_id} unexpected error: {str(e)}")
                self._update_failure_stats()
                raise
            
            finally:
                # Clean up transaction tracking
                if transaction_id in self.active_transactions:
                    del self.active_transactions[transaction_id]
    
    def _update_success_stats(self, duration: float):
        """Update statistics for successful transactions"""
        self.transaction_stats['successful_transactions'] += 1
        
        # Update average duration
        total_successful = self.transaction_stats['successful_transactions']
        current_avg = self.transaction_stats['average_duration']
        self.transaction_stats['average_duration'] = (
            (current_avg * (total_successful - 1) + duration) / total_successful
        )
    
    def _update_failure_stats(self):
        """Update statistics for failed transactions"""
        self.transaction_stats['failed_transactions'] += 1
    
    def bulk_insert_optimized(self, model_class: Type, data_list: List[Dict[str, Any]], 
                            batch_size: int = None) -> Dict[str, Any]:
        """Optimized bulk insert with transaction management"""
        
        batch_size = batch_size or self.config.OPTIMIZATION_BATCH_SIZE
        total_records = len(data_list)
        processed = 0
        failed = 0
        
        start_time = time.time()
        
        try:
            with self.transaction() as session:
                # Process in batches
                for i in range(0, total_records, batch_size):
                    batch = data_list[i:i + batch_size]
                    
                    try:
                        # Use bulk_insert_mappings for better performance
                        session.bulk_insert_mappings(model_class, batch)
                        processed += len(batch)
                        
                        logger.debug(f"Bulk insert batch {i//batch_size + 1}: {len(batch)} records")
                        
                    except Exception as e:
                        logger.error(f"Error in bulk insert batch {i//batch_size + 1}: {str(e)}")
                        failed += len(batch)
                        # Continue with next batch instead of failing entire operation
                        continue
            
            duration = time.time() - start_time
            
            return {
                'success': True,
                'total_records': total_records,
                'processed': processed,
                'failed': failed,
                'duration': duration,
                'records_per_second': processed / duration if duration > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Bulk insert operation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_records': total_records,
                'processed': processed,
                'failed': total_records - processed
            }
    
    def bulk_update_optimized(self, model_class: Type, updates: List[Dict[str, Any]], 
                            batch_size: int = None) -> Dict[str, Any]:
        """Optimized bulk update with transaction management"""
        
        batch_size = batch_size or self.config.OPTIMIZATION_BATCH_SIZE
        total_updates = len(updates)
        processed = 0
        failed = 0
        
        start_time = time.time()
        
        try:
            with self.transaction() as session:
                # Process in batches
                for i in range(0, total_updates, batch_size):
                    batch = updates[i:i + batch_size]
                    
                    try:
                        # Use bulk_update_mappings for better performance
                        session.bulk_update_mappings(model_class, batch)
                        processed += len(batch)
                        
                        logger.debug(f"Bulk update batch {i//batch_size + 1}: {len(batch)} records")
                        
                    except Exception as e:
                        logger.error(f"Error in bulk update batch {i//batch_size + 1}: {str(e)}")
                        failed += len(batch)
                        continue
            
            duration = time.time() - start_time
            
            return {
                'success': True,
                'total_updates': total_updates,
                'processed': processed,
                'failed': failed,
                'duration': duration,
                'updates_per_second': processed / duration if duration > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Bulk update operation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_updates': total_updates,
                'processed': processed,
                'failed': total_updates - processed
            }
    
    def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Execute database operation with retry logic"""
        
        retry_count = 0
        max_retries = self.config.DB_RETRY_ATTEMPTS
        
        while retry_count <= max_retries:
            try:
                return operation(*args, **kwargs)
                
            except (OperationalError, DisconnectionError, SQLTimeoutError) as e:
                retry_count += 1
                self.transaction_stats['retry_count'] += 1
                
                if retry_count <= max_retries:
                    wait_time = min(2 ** retry_count, 10)
                    logger.warning(
                        f"Database operation failed (attempt {retry_count}), "
                        f"retrying in {wait_time}s: {str(e)}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {max_retries} retries: {str(e)}")
                    raise
            
            except Exception as e:
                logger.error(f"Database operation failed with non-retryable error: {str(e)}")
                raise
    
    def get_connection_pool_status(self) -> Dict[str, Any]:
        """Get current connection pool status"""
        try:
            pool = db.engine.pool
            
            return {
                'pool_size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'invalid': pool.invalid(),
                'pool_class': pool.__class__.__name__
            }
        except Exception as e:
            logger.error(f"Error getting pool status: {str(e)}")
            return {'error': str(e)}
    
    def get_transaction_statistics(self) -> Dict[str, Any]:
        """Get transaction statistics"""
        stats = self.transaction_stats.copy()
        
        # Calculate success rate
        total = stats['total_transactions']
        if total > 0:
            stats['success_rate'] = (stats['successful_transactions'] / total) * 100
            stats['failure_rate'] = (stats['failed_transactions'] / total) * 100
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
        
        # Add active transaction count
        stats['active_transactions'] = len(self.active_transactions)
        
        # Add connection pool status
        stats['connection_pool'] = self.get_connection_pool_status()
        
        return stats
    
    def reset_statistics(self):
        """Reset transaction statistics"""
        self.transaction_stats = {
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'rollback_count': 0,
            'retry_count': 0,
            'average_duration': 0.0,
            'last_reset': datetime.utcnow()
        }
        logger.info("Transaction statistics reset")
    
    def cleanup_long_running_transactions(self, max_duration: int = None):
        """Cleanup transactions that have been running too long"""
        max_duration = max_duration or (self.config.DB_TRANSACTION_TIMEOUT * 2)
        current_time = time.time()
        
        long_running = []
        for txn_id, txn_info in self.active_transactions.items():
            duration = current_time - txn_info['start_time']
            if duration > max_duration:
                long_running.append((txn_id, duration))
        
        if long_running:
            logger.warning(f"Found {len(long_running)} long-running transactions")
            for txn_id, duration in long_running:
                logger.warning(f"Long-running transaction {txn_id}: {duration:.2f}s")
        
        return long_running

# Global transaction manager instance
transaction_manager = DatabaseTransactionManager()

def get_transaction_manager() -> DatabaseTransactionManager:
    """Get the global transaction manager instance"""
    return transaction_manager

def optimized_transaction(isolation_level: Optional[str] = None, 
                        timeout: Optional[int] = None, 
                        retry_on_failure: bool = True):
    """Decorator for optimized database transactions"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with transaction_manager.transaction(
                isolation_level=isolation_level,
                timeout=timeout,
                retry_on_failure=retry_on_failure
            ) as session:
                return func(session, *args, **kwargs)
        return wrapper
    return decorator

def retry_on_db_error(max_retries: int = None):
    """Decorator for retrying database operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return transaction_manager.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator