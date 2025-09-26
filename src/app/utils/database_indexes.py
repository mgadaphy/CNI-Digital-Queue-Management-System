"""
Database Index Optimization - Phase 3 Implementation

This module provides database index recommendations and creation scripts
to optimize query performance based on the analysis of current usage patterns.

Key Index Recommendations:
1. Composite indexes for frequently used filter combinations
2. Covering indexes for common SELECT queries
3. Partial indexes for filtered queries
4. Proper index maintenance and monitoring
"""

from sqlalchemy import text, Index
from ..extensions import db
from ..models import Queue, Citizen, Agent, ServiceType, Station
import logging

logger = logging.getLogger(__name__)

class DatabaseIndexOptimizer:
    """Database index optimization and management"""
    
    @staticmethod
    def create_performance_indexes():
        """
        Create performance-optimized indexes based on query analysis
        
        These indexes are designed to optimize the most common query patterns
        identified in the application.
        """
        try:
            # Queue table performance indexes
            queue_indexes = [
                # Composite index for status + priority queries (most common)
                Index('idx_queue_status_priority_created', 
                      Queue.status, Queue.priority_score.desc(), Queue.created_at),
                
                # Composite index for agent assignment queries
                Index('idx_queue_agent_status', 
                      Queue.agent_id, Queue.status),
                
                # Composite index for service type + status queries
                Index('idx_queue_service_status_priority', 
                      Queue.service_type_id, Queue.status, Queue.priority_score.desc()),
                
                # Composite index for citizen + status queries
                Index('idx_queue_citizen_status_created', 
                      Queue.citizen_id, Queue.status, Queue.created_at.desc()),
                
                # Index for date-based queries (completed tickets)
                Index('idx_queue_completed_date', 
                      Queue.status, Queue.completed_at.desc()),
                
                # Covering index for dashboard queries
                Index('idx_queue_dashboard_covering', 
                      Queue.status, Queue.priority_score.desc(), Queue.created_at,
                      Queue.citizen_id, Queue.service_type_id, Queue.agent_id)
            ]
            
            # Citizen table performance indexes
            citizen_indexes = [
                # Unique index on pre_enrollment_code (already exists but ensure it's optimized)
                Index('idx_citizen_enrollment_active', 
                      Citizen.pre_enrollment_code, Citizen.is_active),
                
                # Index for name searches
                Index('idx_citizen_names', 
                      Citizen.first_name, Citizen.last_name),
                
                # Index for date-based queries
                Index('idx_citizen_created_active', 
                      Citizen.created_at.desc(), Citizen.is_active)
            ]
            
            # Agent table performance indexes
            agent_indexes = [
                # Composite index for status + station queries
                Index('idx_agent_status_station', 
                      Agent.status, Agent.current_station_id),
                
                # Index for employee lookup
                Index('idx_agent_employee_active', 
                      Agent.employee_id, Agent.is_active),
                
                # Index for performance queries
                Index('idx_agent_active_status_created', 
                      Agent.is_active, Agent.status, Agent.created_at)
            ]
            
            # Create all indexes
            all_indexes = queue_indexes + citizen_indexes + agent_indexes
            
            created_count = 0
            for index in all_indexes:
                try:
                    # Check if index already exists
                    if not DatabaseIndexOptimizer._index_exists(index.name):
                        index.create(db.engine)
                        created_count += 1
                        logger.info(f"Created index: {index.name}")
                    else:
                        logger.debug(f"Index already exists: {index.name}")
                        
                except Exception as e:
                    logger.warning(f"Failed to create index {index.name}: {e}")
                    continue
            
            logger.info(f"Database index optimization completed. Created {created_count} new indexes.")
            return created_count
            
        except Exception as e:
            logger.error(f"Error in create_performance_indexes: {e}")
            return 0
    
    @staticmethod
    def _index_exists(index_name: str) -> bool:
        """Check if an index exists in the database"""
        try:
            # PostgreSQL specific query to check index existence
            result = db.engine.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = :index_name
                )
            """), index_name=index_name)
            
            return result.scalar()
            
        except Exception as e:
            logger.warning(f"Could not check index existence for {index_name}: {e}")
            return False
    
    @staticmethod
    def analyze_query_performance():
        """
        Analyze current query performance and provide recommendations
        
        Returns a report of slow queries and optimization suggestions.
        """
        try:
            # Get slow query statistics (PostgreSQL specific)
            slow_queries = db.engine.execute(text("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    rows
                FROM pg_stat_statements 
                WHERE mean_time > 100  -- Queries taking more than 100ms on average
                ORDER BY mean_time DESC 
                LIMIT 10
            """)).fetchall()
            
            # Get table statistics
            table_stats = db.engine.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    seq_scan,
                    seq_tup_read,
                    idx_scan,
                    idx_tup_fetch
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY seq_scan DESC
            """)).fetchall()
            
            # Get index usage statistics
            index_stats = db.engine.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
            """)).fetchall()
            
            return {
                'slow_queries': [dict(row) for row in slow_queries],
                'table_stats': [dict(row) for row in table_stats],
                'index_stats': [dict(row) for row in index_stats],
                'recommendations': DatabaseIndexOptimizer._generate_recommendations(table_stats)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing query performance: {e}")
            return {
                'error': str(e),
                'recommendations': ['Enable pg_stat_statements extension for detailed query analysis']
            }
    
    @staticmethod
    def _generate_recommendations(table_stats) -> list:
        """Generate optimization recommendations based on table statistics"""
        recommendations = []
        
        for stat in table_stats:
            table_name = stat['tablename']
            seq_scans = stat['seq_scan']
            idx_scans = stat['idx_scan'] or 0
            
            # High sequential scan ratio indicates missing indexes
            if seq_scans > 0 and (idx_scans / max(seq_scans, 1)) < 0.1:
                recommendations.append(
                    f"Table '{table_name}' has high sequential scan ratio ({seq_scans} seq vs {idx_scans} idx). "
                    f"Consider adding indexes on frequently filtered columns."
                )
            
            # High insert/update activity might benefit from partial indexes
            inserts = stat['inserts']
            updates = stat['updates']
            if inserts + updates > 10000:
                recommendations.append(
                    f"Table '{table_name}' has high write activity ({inserts + updates} operations). "
                    f"Consider using partial indexes to reduce index maintenance overhead."
                )
        
        if not recommendations:
            recommendations.append("Database performance appears optimal based on current statistics.")
        
        return recommendations
    
    @staticmethod
    def create_partial_indexes():
        """
        Create partial indexes for common filtered queries
        
        Partial indexes are smaller and faster for specific query patterns.
        """
        try:
            partial_indexes = [
                # Partial index for active waiting tickets (most common query)
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_queue_waiting_priority "
                "ON queue (priority_score DESC, created_at) "
                "WHERE status = 'waiting'",
                
                # Partial index for active citizens
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_citizen_active_enrollment "
                "ON citizens (pre_enrollment_code) "
                "WHERE is_active = true",
                
                # Partial index for available agents
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_agent_available "
                "ON agents (id, current_station_id) "
                "WHERE status = 'available' AND is_active = true",
                
                # Partial index for today's completed tickets
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_queue_completed_today "
                "ON queue (completed_at DESC, agent_id) "
                "WHERE status = 'completed' AND completed_at >= CURRENT_DATE"
            ]
            
            created_count = 0
            for sql in partial_indexes:
                try:
                    db.engine.execute(text(sql))
                    created_count += 1
                    logger.info(f"Created partial index: {sql.split()[5]}")
                    
                except Exception as e:
                    logger.warning(f"Failed to create partial index: {e}")
                    continue
            
            logger.info(f"Created {created_count} partial indexes.")
            return created_count
            
        except Exception as e:
            logger.error(f"Error creating partial indexes: {e}")
            return 0
    
    @staticmethod
    def optimize_database_settings():
        """
        Provide database configuration recommendations for better performance
        """
        recommendations = {
            'postgresql_settings': {
                'shared_buffers': '256MB',  # Adjust based on available RAM
                'effective_cache_size': '1GB',  # Adjust based on available RAM
                'work_mem': '4MB',  # For sorting and hash operations
                'maintenance_work_mem': '64MB',  # For VACUUM, CREATE INDEX
                'checkpoint_completion_target': '0.9',  # Spread checkpoint I/O
                'wal_buffers': '16MB',  # Write-ahead log buffers
                'default_statistics_target': '100',  # Query planner statistics
                'random_page_cost': '1.1',  # SSD optimization
                'effective_io_concurrency': '200'  # SSD optimization
            },
            'maintenance_tasks': [
                'VACUUM ANALYZE queue;',  # Update table statistics
                'VACUUM ANALYZE citizens;',
                'VACUUM ANALYZE agents;',
                'REINDEX INDEX CONCURRENTLY idx_queue_status_priority_created;',  # Rebuild key indexes
                'UPDATE pg_stat_statements_reset();'  # Reset query statistics
            ],
            'monitoring_queries': [
                "SELECT * FROM pg_stat_activity WHERE state = 'active';",  # Active queries
                "SELECT * FROM pg_locks WHERE NOT granted;",  # Lock conflicts
                "SELECT * FROM pg_stat_user_tables WHERE n_tup_upd + n_tup_ins + n_tup_del > 1000;"  # High activity tables
            ]
        }
        
        return recommendations

# Global instance for easy import
db_optimizer = DatabaseIndexOptimizer()
