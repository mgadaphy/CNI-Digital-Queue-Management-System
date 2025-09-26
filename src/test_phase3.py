#!/usr/bin/env python3
"""
Phase 3 Database Optimization Testing

This script tests the database query optimizations implemented in Phase 3
and measures performance improvements.
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Queue, Citizen, ServiceType, Agent
from app.utils.optimized_queries import query_optimizer
from app.utils.database_indexes import db_optimizer

def measure_query_performance(func, *args, **kwargs):
    """Measure query execution time"""
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
    return result, execution_time

def test_optimized_vs_original_queries():
    """Compare performance of optimized vs original queries"""
    print("🔍 Testing Query Performance Comparison...")
    
    results = {}
    
    # Test 1: Dashboard data retrieval
    print("\n📊 Test 1: Dashboard Data Retrieval")
    
    # Original approach (multiple separate queries)
    def original_dashboard():
        total_waiting = Queue.query.filter_by(status='waiting').count()
        total_in_progress = Queue.query.filter_by(status='in_progress').count()
        total_completed = Queue.query.filter_by(status='completed').count()
        
        # Get recent tickets with N+1 problem
        tickets = Queue.query.filter(
            Queue.status.in_(['waiting', 'in_progress'])
        ).limit(20).all()
        
        # This causes N+1 queries for each ticket's citizen and service_type
        for ticket in tickets:
            _ = ticket.citizen.first_name if ticket.citizen else None
            _ = ticket.service_type.name_fr if ticket.service_type else None
        
        return {
            'waiting': total_waiting,
            'in_progress': total_in_progress,
            'completed': total_completed,
            'tickets': tickets
        }
    
    # Optimized approach
    def optimized_dashboard():
        return query_optimizer.get_dashboard_data()
    
    # Measure performance
    _, original_time = measure_query_performance(original_dashboard)
    _, optimized_time = measure_query_performance(optimized_dashboard)
    
    improvement = ((original_time - optimized_time) / original_time) * 100
    
    print(f"  📈 Original approach: {original_time:.2f}ms")
    print(f"  ⚡ Optimized approach: {optimized_time:.2f}ms")
    print(f"  🎯 Performance improvement: {improvement:.1f}%")
    
    results['dashboard'] = {
        'original_ms': original_time,
        'optimized_ms': optimized_time,
        'improvement_percent': improvement
    }
    
    # Test 2: Ticket refresh with pagination
    print("\n📋 Test 2: Ticket Refresh with Pagination")
    
    def original_refresh():
        # Original query with outerjoin (can be slow)
        query = Queue.query.outerjoin(Citizen).outerjoin(ServiceType).outerjoin(Agent)
        paginated = query.order_by(Queue.priority_score.desc(), Queue.created_at).paginate(
            page=1, per_page=50, error_out=False
        )
        
        # Process results (causes additional queries)
        tickets_data = []
        for ticket in paginated.items:
            citizen_name = f"{ticket.citizen.first_name} {ticket.citizen.last_name}" if ticket.citizen else "Unknown"
            service_name = ticket.service_type.name_fr if ticket.service_type else "Unknown"
            tickets_data.append({
                'citizen_name': citizen_name,
                'service_name': service_name,
                'priority': ticket.priority_score
            })
        
        return tickets_data
    
    def optimized_refresh():
        return query_optimizer.refresh_tickets_optimized(page=1, per_page=50)
    
    _, original_time = measure_query_performance(original_refresh)
    _, optimized_time = measure_query_performance(optimized_refresh)
    
    improvement = ((original_time - optimized_time) / original_time) * 100
    
    print(f"  📈 Original approach: {original_time:.2f}ms")
    print(f"  ⚡ Optimized approach: {optimized_time:.2f}ms")
    print(f"  🎯 Performance improvement: {improvement:.1f}%")
    
    results['refresh'] = {
        'original_ms': original_time,
        'optimized_ms': optimized_time,
        'improvement_percent': improvement
    }
    
    # Test 3: Queue position calculation
    print("\n🎯 Test 3: Queue Position Calculation")
    
    # Get a test ticket
    test_ticket = Queue.query.filter_by(status='waiting').first()
    if test_ticket:
        def original_position():
            # Original approach with multiple queries
            tickets_ahead = Queue.query.filter(
                Queue.status == 'waiting',
                Queue.priority_score > test_ticket.priority_score
            ).count()
            
            same_priority_ahead = Queue.query.filter(
                Queue.status == 'waiting',
                Queue.priority_score == test_ticket.priority_score,
                Queue.created_at < test_ticket.created_at
            ).count()
            
            return tickets_ahead + same_priority_ahead + 1
        
        def optimized_position():
            result = query_optimizer.queue_queries.get_citizen_queue_position(
                test_ticket.citizen_id, test_ticket.id
            )
            return result.get('position')
        
        _, original_time = measure_query_performance(original_position)
        _, optimized_time = measure_query_performance(optimized_position)
        
        improvement = ((original_time - optimized_time) / original_time) * 100
        
        print(f"  📈 Original approach: {original_time:.2f}ms")
        print(f"  ⚡ Optimized approach: {optimized_time:.2f}ms")
        print(f"  🎯 Performance improvement: {improvement:.1f}%")
        
        results['position'] = {
            'original_ms': original_time,
            'optimized_ms': optimized_time,
            'improvement_percent': improvement
        }
    else:
        print("  ⚠️ No waiting tickets found for position test")
        results['position'] = {'error': 'No test data'}
    
    return results

def test_database_indexes():
    """Test database index creation and optimization"""
    print("\n🗂️ Testing Database Index Optimization...")
    
    try:
        # Create performance indexes
        created_indexes = db_optimizer.create_performance_indexes()
        print(f"  ✅ Created {created_indexes} performance indexes")
        
        # Create partial indexes
        created_partial = db_optimizer.create_partial_indexes()
        print(f"  ✅ Created {created_partial} partial indexes")
        
        # Get performance analysis
        analysis = db_optimizer.analyze_query_performance()
        
        if 'error' not in analysis:
            print(f"  📊 Found {len(analysis.get('slow_queries', []))} slow queries")
            print(f"  📋 Analyzed {len(analysis.get('table_stats', []))} tables")
            print(f"  🎯 Generated {len(analysis.get('recommendations', []))} recommendations")
            
            # Show top recommendations
            recommendations = analysis.get('recommendations', [])[:3]
            for i, rec in enumerate(recommendations, 1):
                print(f"    {i}. {rec}")
        else:
            print(f"  ⚠️ Analysis error: {analysis['error']}")
        
        return {
            'indexes_created': created_indexes,
            'partial_indexes_created': created_partial,
            'analysis': analysis
        }
        
    except Exception as e:
        print(f"  ❌ Index optimization error: {e}")
        return {'error': str(e)}

def test_query_scalability():
    """Test query performance with different data sizes"""
    print("\n📈 Testing Query Scalability...")
    
    # Test with different page sizes
    page_sizes = [10, 50, 100, 200]
    scalability_results = {}
    
    for page_size in page_sizes:
        print(f"  📄 Testing with page size: {page_size}")
        
        _, execution_time = measure_query_performance(
            query_optimizer.refresh_tickets_optimized,
            page=1,
            per_page=page_size
        )
        
        scalability_results[page_size] = execution_time
        print(f"    ⏱️ Execution time: {execution_time:.2f}ms")
    
    # Calculate scalability factor
    base_time = scalability_results[10]
    max_time = scalability_results[200]
    scalability_factor = max_time / base_time
    
    print(f"  📊 Scalability factor (200 vs 10 records): {scalability_factor:.2f}x")
    
    if scalability_factor < 5:
        print("  ✅ Good scalability - linear growth")
    elif scalability_factor < 10:
        print("  ⚠️ Moderate scalability - some optimization needed")
    else:
        print("  ❌ Poor scalability - significant optimization required")
    
    return scalability_results

def generate_performance_report(results):
    """Generate a comprehensive performance report"""
    print("\n📋 Phase 3 Performance Report")
    print("=" * 50)
    
    total_improvement = 0
    test_count = 0
    
    for test_name, test_results in results.items():
        if isinstance(test_results, dict) and 'improvement_percent' in test_results:
            improvement = test_results['improvement_percent']
            total_improvement += improvement
            test_count += 1
            
            print(f"\n🧪 {test_name.title()} Test:")
            print(f"  📈 Performance improvement: {improvement:.1f}%")
            print(f"  ⏱️ Time reduction: {test_results['original_ms'] - test_results['optimized_ms']:.2f}ms")
    
    if test_count > 0:
        avg_improvement = total_improvement / test_count
        print(f"\n🎯 Average Performance Improvement: {avg_improvement:.1f}%")
        
        if avg_improvement > 50:
            print("🏆 Excellent optimization results!")
        elif avg_improvement > 25:
            print("✅ Good optimization results!")
        elif avg_improvement > 10:
            print("👍 Moderate optimization results")
        else:
            print("⚠️ Limited optimization impact")
    
    # Database optimization summary
    if 'database' in results:
        db_results = results['database']
        if 'error' not in db_results:
            print(f"\n🗂️ Database Optimization:")
            print(f"  📊 Indexes created: {db_results.get('indexes_created', 0)}")
            print(f"  🎯 Partial indexes: {db_results.get('partial_indexes_created', 0)}")
    
    print(f"\n⏰ Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def run_phase3_tests():
    """Run comprehensive Phase 3 testing"""
    print("🚀 Starting Phase 3: Database Query Optimization Tests")
    print("=" * 60)
    
    try:
        # Test query performance
        query_results = test_optimized_vs_original_queries()
        
        # Test database indexes
        db_results = test_database_indexes()
        
        # Test scalability
        scalability_results = test_query_scalability()
        
        # Combine all results
        all_results = {
            **query_results,
            'database': db_results,
            'scalability': scalability_results
        }
        
        # Generate report
        generate_performance_report(all_results)
        
        print("\n🎉 Phase 3 Testing Complete!")
        return all_results
        
    except Exception as e:
        print(f"\n❌ Phase 3 testing failed: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_phase3_tests()
