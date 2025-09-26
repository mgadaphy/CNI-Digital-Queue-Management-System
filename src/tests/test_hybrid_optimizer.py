import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app import create_app
from app.extensions import db
from app.models import Citizen, ServiceType, Queue, Agent
from app.queue_logic.hybrid_optimizer import (
    HybridOptimizationEngine, PriorityMatrix, DynamicLoadBalancer,
    IntelligentRouter, PriorityLevel, SystemState
)
from app.queue_logic.optimizer import (
    calculate_priority_score, get_next_citizen_in_queue,
    process_citizen_checkin, get_system_performance_metrics
)

class TestHybridOptimizer(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Create test data
        self.service_type_emergency = ServiceType(
            id=1, code='EMERGENCY', name_fr='Urgence', name_en='Emergency',
            priority_level=1, estimated_duration=12
        )
        self.service_type_renewal = ServiceType(
            id=2, code='RENEWAL', name_fr='Renouvellement', name_en='Renewal',
            priority_level=4, estimated_duration=10
        )
        self.service_type_collection = ServiceType(
            id=3, code='COLLECTION', name_fr='Collecte', name_en='Collection',
            priority_level=3, estimated_duration=3
        )
        
        from datetime import date
        self.citizen1 = Citizen(
            id=1, pre_enrollment_code='PRE001', first_name='John', last_name='Doe',
            date_of_birth=date(1990, 1, 1), email='john@example.com', phone_number='+1234567890'
        )
        self.citizen2 = Citizen(
            id=2, pre_enrollment_code='PRE002', first_name='Jane', last_name='Smith',
            date_of_birth=date(1985, 5, 15), email='jane@example.com', phone_number='+0987654321'
        )
        
        self.agent1 = Agent(
            id=1, employee_id='A-001', first_name='Agent', last_name='One',
            email='agent1@example.com', phone='+1111111111',
            status='available', role='agent'
        )
        self.agent2 = Agent(
            id=2, employee_id='A-002', first_name='Agent', last_name='Two',
            email='agent2@example.com', phone='+2222222222',
            status='busy', role='agent'
        )
        
        db.session.add_all([
            self.service_type_emergency, self.service_type_renewal, self.service_type_collection,
            self.citizen1, self.citizen2, self.agent1, self.agent2
        ])
        db.session.commit()
        
        # Initialize optimization engine
        self.engine = HybridOptimizationEngine()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_priority_matrix_basic_calculation(self):
        """Test basic priority score calculation"""
        priority_matrix = PriorityMatrix()
        
        # Test emergency priority
        score = priority_matrix.calculate_priority_score(
            self.citizen1, self.service_type_emergency
        )
        self.assertEqual(score, 1000)  # Emergency base priority
        
        # Test renewal priority
        score = priority_matrix.calculate_priority_score(
            self.citizen1, self.service_type_renewal
        )
        self.assertEqual(score, 400)  # Renewal base priority
    
    def test_priority_matrix_with_wait_time(self):
        """Test priority calculation with wait time bonus"""
        priority_matrix = PriorityMatrix()
        
        # Test with 30 minutes wait time
        score = priority_matrix.calculate_priority_score(
            self.citizen1, self.service_type_renewal, wait_time_minutes=30
        )
        expected = 400 + (30 * 2)  # Base + wait bonus
        self.assertEqual(score, expected)
        
        # Test with very long wait time (should cap at 200)
        score = priority_matrix.calculate_priority_score(
            self.citizen1, self.service_type_renewal, wait_time_minutes=200
        )
        expected = 400 + 200  # Base + max wait bonus
        self.assertEqual(score, expected)
    
    def test_priority_matrix_with_special_factors(self):
        """Test priority calculation with special factors"""
        priority_matrix = PriorityMatrix()
        
        special_factors = {
            'elderly': True,
            'disability': True,
            'pregnant': False
        }
        
        score = priority_matrix.calculate_priority_score(
            self.citizen1, self.service_type_renewal, special_factors=special_factors
        )
        expected = 400 + 100 + 150  # Base + elderly + disability
        self.assertEqual(score, expected)
    
    def test_dynamic_load_balancer_system_state(self):
        """Test system state calculation"""
        # Create some queue entries
        queue1 = Queue(
            citizen_id=1, service_type_id=1, ticket_number='T001',
            priority_score=1000, status='waiting'
        )
        queue2 = Queue(
            citizen_id=2, service_type_id=2, ticket_number='T002',
            priority_score=400, status='waiting'
        )
        db.session.add_all([queue1, queue2])
        db.session.commit()
        
        load_balancer = DynamicLoadBalancer()
        system_state = load_balancer.get_system_state()
        
        self.assertEqual(system_state.total_waiting, 2)
        self.assertEqual(system_state.agents_available, 1)
        self.assertEqual(system_state.agents_busy, 1)
        self.assertIsInstance(system_state.average_wait_time, float)
        self.assertIsInstance(system_state.peak_hours, bool)
    
    def test_dynamic_load_balancer_agent_workload(self):
        """Test agent workload calculation"""
        # Create queue entries assigned to agent
        queue1 = Queue(
            citizen_id=1, service_type_id=1, ticket_number='T001',
            priority_score=1000, status='in_progress', agent_id=1
        )
        queue2 = Queue(
            citizen_id=2, service_type_id=2, ticket_number='T002',
            priority_score=400, status='waiting', agent_id=1
        )
        db.session.add_all([queue1, queue2])
        db.session.commit()
        
        load_balancer = DynamicLoadBalancer()
        workload = load_balancer.calculate_agent_workload(1)
        
        expected = (1 * 2) + 1  # 1 in_progress * 2 + 1 waiting
        self.assertEqual(workload, expected)
    
    def test_dynamic_load_balancer_optimal_agent(self):
        """Test optimal agent selection"""
        load_balancer = DynamicLoadBalancer()
        system_state = load_balancer.get_system_state()
        
        optimal_agent_id = load_balancer.find_optimal_agent(
            self.service_type_renewal, system_state
        )
        
        # Should return available agent (agent1)
        self.assertEqual(optimal_agent_id, 1)
    
    def test_intelligent_router_wait_time_estimation(self):
        """Test wait time estimation"""
        # Create higher priority queue entry
        high_priority_queue = Queue(
            citizen_id=2, service_type_id=1, ticket_number='T002',
            priority_score=1000, status='waiting'
        )
        db.session.add(high_priority_queue)
        db.session.commit()
        
        router = IntelligentRouter()
        load_balancer = DynamicLoadBalancer()
        system_state = load_balancer.get_system_state()
        
        wait_time = router.estimate_wait_time(
            self.citizen1, self.service_type_renewal, system_state
        )
        
        self.assertIsInstance(wait_time, int)
        self.assertGreater(wait_time, 0)
    
    def test_intelligent_router_queue_position(self):
        """Test queue position calculation"""
        # Create higher priority queue entries
        queue1 = Queue(
            citizen_id=1, service_type_id=1, ticket_number='T001',
            priority_score=1000, status='waiting'
        )
        queue2 = Queue(
            citizen_id=2, service_type_id=1, ticket_number='T002',
            priority_score=800, status='waiting'
        )
        db.session.add_all([queue1, queue2])
        db.session.commit()
        
        router = IntelligentRouter()
        
        # Test position for priority 500 (should be 3rd)
        position = router.calculate_queue_position(500)
        self.assertEqual(position, 3)
        
        # Test position for priority 1200 (should be 1st)
        position = router.calculate_queue_position(1200)
        self.assertEqual(position, 1)
    
    def test_hybrid_optimization_engine_checkin(self):
        """Test complete check-in process"""
        result = self.engine.process_checkin(
            self.citizen1, self.service_type_emergency
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result.recommended_agent_id, 1)  # Available agent
        self.assertGreater(result.priority_score, 0)
        self.assertGreater(result.estimated_wait_time, 0)
        self.assertEqual(result.queue_position, 1)  # First in queue
        self.assertIsInstance(result.optimization_factors, dict)
    
    def test_hybrid_optimization_engine_checkin_with_special_factors(self):
        """Test check-in with special factors"""
        special_factors = {
            'elderly': True,
            'disability': False,
            'pregnant': True
        }
        
        result = self.engine.process_checkin(
            self.citizen1, self.service_type_renewal, special_factors
        )
        
        # Should have higher priority due to special factors
        expected_base = 400 + 100 + 120  # Base + elderly + pregnant
        self.assertEqual(result.priority_score, expected_base)
    
    def test_hybrid_optimization_engine_reoptimize(self):
        """Test queue reoptimization"""
        # Create old queue entry
        old_time = datetime.utcnow() - timedelta(minutes=30)
        queue_entry = Queue(
            citizen_id=1, service_type_id=2, ticket_number='T001',
            priority_score=400, status='waiting', created_at=old_time
        )
        db.session.add(queue_entry)
        db.session.commit()
        
        results = self.engine.reoptimize_queue()
        
        self.assertIsInstance(results, list)
        if results:  # If optimization occurred
            self.assertIn('queue_id', results[0])
            self.assertIn('new_priority', results[0])
    
    def test_hybrid_optimization_engine_performance_metrics(self):
        """Test performance metrics calculation"""
        metrics = self.engine.get_performance_metrics()
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_waiting', metrics)
        self.assertIn('average_wait_time', metrics)
        self.assertIn('agent_utilization', metrics)
        self.assertIn('service_balance', metrics)
        self.assertIn('peak_hours_active', metrics)
        self.assertIn('agents_available', metrics)
        self.assertIn('agents_busy', metrics)
    
    def test_optimizer_integration_calculate_priority_score(self):
        """Test integration with existing optimizer functions"""
        score = calculate_priority_score(self.citizen1, self.service_type_emergency)
        
        self.assertIsInstance(score, (int, float))
        self.assertEqual(score, 1000)  # Emergency priority
    
    def test_optimizer_integration_get_next_citizen(self):
        """Test integration with get_next_citizen_in_queue"""
        # Create queue entries
        queue1 = Queue(
            citizen_id=1, service_type_id=1, ticket_number='T001',
            priority_score=1000, status='waiting'
        )
        queue2 = Queue(
            citizen_id=2, service_type_id=2, ticket_number='T002',
            priority_score=400, status='waiting'
        )
        db.session.add_all([queue1, queue2])
        db.session.commit()
        
        next_citizen = get_next_citizen_in_queue()
        
        self.assertIsNotNone(next_citizen)
        self.assertEqual(next_citizen.citizen_id, 1)  # Higher priority
    
    def test_optimizer_integration_process_checkin(self):
        """Test integration with process_citizen_checkin"""
        result = process_citizen_checkin(
            self.citizen1, self.service_type_emergency
        )
        
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.priority_score)
        self.assertIsNotNone(result.estimated_wait_time)
    
    def test_optimizer_integration_performance_metrics(self):
        """Test integration with get_system_performance_metrics"""
        metrics = get_system_performance_metrics()
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_waiting', metrics)
    
    @patch('app.queue_logic.hybrid_optimizer.logger')
    def test_error_handling_and_fallbacks(self, mock_logger):
        """Test error handling and fallback mechanisms"""
        # Test with invalid service type
        invalid_service = ServiceType(
            id=999, code='INVALID', name_fr='Invalid', name_en='Invalid',
            priority_level=999, estimated_duration=0
        )
        
        # Should not raise exception
        score = calculate_priority_score(self.citizen1, invalid_service)
        self.assertIsInstance(score, float)
    
    def test_peak_hours_detection(self):
        """Test peak hours detection logic"""
        load_balancer = DynamicLoadBalancer()
        
        # Mock different hours
        with patch('app.queue_logic.hybrid_optimizer.datetime') as mock_datetime:
            # Test peak hour (10 AM)
            mock_datetime.now.return_value.hour = 10
            system_state = load_balancer.get_system_state()
            self.assertTrue(system_state.peak_hours)
            
            # Test non-peak hour (8 AM)
            mock_datetime.now.return_value.hour = 8
            system_state = load_balancer.get_system_state()
            self.assertFalse(system_state.peak_hours)
    
    def test_service_distribution_calculation(self):
        """Test service distribution calculation"""
        # Create queue entries for different services
        queue1 = Queue(
            citizen_id=1, service_type_id=1, ticket_number='T001',
            priority_score=1000, status='waiting'
        )
        queue2 = Queue(
            citizen_id=2, service_type_id=2, ticket_number='T002',
            priority_score=400, status='waiting'
        )
        db.session.add_all([queue1, queue2])
        db.session.commit()
        
        load_balancer = DynamicLoadBalancer()
        system_state = load_balancer.get_system_state()
        
        self.assertIn('EMERGENCY', system_state.service_distribution)
        self.assertIn('RENEWAL', system_state.service_distribution)
        self.assertEqual(system_state.service_distribution['EMERGENCY'], 1)
        self.assertEqual(system_state.service_distribution['RENEWAL'], 1)

if __name__ == '__main__':
    unittest.main()