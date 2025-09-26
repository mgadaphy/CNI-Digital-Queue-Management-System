import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os
import uuid

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models import Agent, ServiceType, Citizen, Queue
from app.queue_logic.intelligent_assignment import (
    IntelligentAgentAssignment, AssignmentStrategy, AssignmentResult,
    AgentCapability, AgentPerformanceAnalyzer, WorkloadAnalyzer
)
from app.extensions import db
from app import create_app


class TestIntelligentAssignment(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with self.app.app_context():
            db.create_all()
            
            # Create test service types with unique codes
            test_id = str(uuid.uuid4())[:8]
            
            self.service_type_passport = ServiceType(
                code=f'PASSPORT_NEW_{test_id}',
                name_fr='Nouvelle demande de passeport',
                name_en='New Passport Application',
                description_fr='Demande de nouveau passeport',
                description_en='New passport application',
                priority_level=3,
                estimated_duration=15,
                required_documents='ID,Birth Certificate',
                is_active=True
            )
            
            self.service_type_renewal = ServiceType(
                code=f'PASSPORT_RENEWAL_{test_id}',
                name_fr='Renouvellement de passeport',
                name_en='Passport Renewal',
                description_fr='Renouvellement de passeport existant',
                description_en='Renewal of existing passport',
                priority_level=2,
                estimated_duration=10,
                required_documents='Old Passport,ID',
                is_active=True
            )
            
            db.session.add(self.service_type_passport)
            db.session.add(self.service_type_renewal)
            
            # Create test agents with unique identifiers
            test_id = str(uuid.uuid4())[:8]
            
            self.agent1 = Agent(
                employee_id=f'EMP001_{test_id}',
                first_name='John',
                last_name='Doe',
                email=f'john.doe.{test_id}@example.com',
                phone='1234567890',
                role='agent',
                specializations='PASSPORT_NEW,PASSPORT_RENEWAL',
                status='available',
                is_active=True
            )
            
            self.agent2 = Agent(
                employee_id=f'EMP002_{test_id}',
                first_name='Jane',
                last_name='Smith',
                email=f'jane.smith.{test_id}@example.com',
                phone='0987654321',
                role='agent',
                specializations='PASSPORT_RENEWAL',
                status='available',
                is_active=True
            )
            
            self.agent3 = Agent(
                employee_id=f'EMP003_{test_id}',
                first_name='Bob',
                last_name='Wilson',
                email=f'bob.wilson.{test_id}@example.com',
                phone='5555555555',
                role='agent',
                specializations='PASSPORT_NEW',
                status='busy',
                is_active=True
            )
            
            db.session.add(self.agent1)
            db.session.add(self.agent2)
            db.session.add(self.agent3)
            
            # Create test citizen
            self.citizen = Citizen(
                pre_enrollment_code=f'TEST001_{test_id}',
                first_name='Test',
                last_name='User',
                email=f'test.{test_id}@example.com',
                phone_number='1111111111',
                date_of_birth=datetime(1990, 1, 1)
            )
            
            db.session.add(self.citizen)
            db.session.commit()
            
            self.intelligent_assignment = IntelligentAgentAssignment()
    
    def tearDown(self):
        """Clean up after each test."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_agent_capability_evaluation(self):
        """Test agent capability evaluation."""
        with self.app.app_context():
            # Refresh objects to ensure they're attached to the current session
            agent1 = db.session.merge(self.agent1)
            service_type = db.session.merge(self.service_type_passport)
            
            capability = self.intelligent_assignment.evaluate_agent_capability(
                agent1, service_type, AssignmentStrategy.SPECIALIZATION_FIRST
            )
            
            self.assertIsInstance(capability, AgentCapability)
            self.assertEqual(capability.agent_id, agent1.id)
            self.assertGreater(capability.specialization_match, 0)
            self.assertGreaterEqual(capability.total_score, 0)
    
    def test_specialization_first_strategy(self):
        """Test specialization-first assignment strategy."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            agent1 = db.session.merge(self.agent1)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.SPECIALIZATION_FIRST
            )
            
            self.assertIsInstance(result, AssignmentResult)
            # Should prefer agent1 who has PASSPORT_NEW specialization and is available
            self.assertEqual(result.agent_id, agent1.id)
            self.assertGreater(result.confidence_score, 0)
            self.assertIn('specialization', result.assignment_reason.lower())
    
    def test_workload_balanced_strategy(self):
        """Test workload-balanced assignment strategy."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_renewal)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.LOAD_BALANCED
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertIsNotNone(result.agent_id)
            self.assertGreater(result.confidence_score, 0)
            self.assertIn('workload', result.assignment_reason.lower())
    
    def test_performance_optimized_strategy(self):
        """Test performance-optimized assignment strategy."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.PERFORMANCE_BASED
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertIsNotNone(result.agent_id)
            self.assertGreater(result.confidence_score, 0)
            self.assertIn('performance', result.assignment_reason.lower())
    
    def test_hybrid_strategy(self):
        """Test hybrid assignment strategy."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.HYBRID
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertIsNotNone(result.agent_id)
            self.assertGreater(result.confidence_score, 0)
            self.assertTrue(len(result.assignment_reason) > 0)
    
    def test_exclude_agents_functionality(self):
        """Test that excluded agents are not assigned."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            agent1 = db.session.merge(self.agent1)
            
            # Exclude agent1
            result = self.intelligent_assignment.find_best_agent(
                service_type, 
                AssignmentStrategy.SPECIALIZATION_FIRST,
                exclude_agents=[agent1.id]
            )
            
            self.assertIsInstance(result, AssignmentResult)
            # Should not assign agent1
            self.assertNotEqual(result.agent_id, agent1.id)
    
    def test_no_available_agents(self):
        """Test behavior when no agents are available."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            
            # Set all agents to busy
            Agent.query.update({'status': 'busy'})
            db.session.commit()
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.HYBRID
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertIsNone(result.agent_id)
            self.assertEqual(result.confidence_score, 0.0)
            self.assertIn('no available agents', result.assignment_reason.lower())
    
    def test_alternative_agents_provided(self):
        """Test that alternative agents are provided in results."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.HYBRID
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertIsInstance(result.alternative_agents, list)
            # Should have at least one alternative if multiple agents available
            available_agents = Agent.query.filter_by(status='available').count()
            if available_agents > 1:
                self.assertGreater(len(result.alternative_agents), 0)
    
    def test_estimated_service_time_calculation(self):
        """Test that estimated service time is calculated correctly."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.HYBRID
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertGreater(result.estimated_service_time, 0)
            # Should be close to the service type's estimated duration
            self.assertLessEqual(
                abs(result.estimated_service_time - service_type.estimated_duration),
                10  # Allow 10 minute variance
            )
    
    def test_workload_impact_calculation(self):
        """Test that workload impact is calculated."""
        with self.app.app_context():
            service_type = db.session.merge(self.service_type_passport)
            
            result = self.intelligent_assignment.find_best_agent(
                service_type, AssignmentStrategy.LOAD_BALANCED
            )
            
            self.assertIsInstance(result, AssignmentResult)
            self.assertIsInstance(result.workload_impact, (int, float))
            self.assertGreaterEqual(result.workload_impact, 0)
    
    @patch('app.queue_logic.intelligent_assignment.datetime')
    def test_performance_analyzer_with_mock_data(self, mock_datetime):
        """Test performance analyzer with mocked historical data."""
        mock_datetime.now.return_value = datetime(2024, 1, 15, 10, 0, 0)
        
        with self.app.app_context():
            analyzer = AgentPerformanceAnalyzer()
            agent1 = db.session.merge(self.agent1)
            
            # Test with no historical data
            score = analyzer.get_agent_performance_score(agent1.id)
            self.assertIsInstance(score, (int, float))
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)
    
    def test_workload_analyzer_current_workload(self):
        """Test workload analyzer current workload calculation."""
        with self.app.app_context():
            # Refresh agent from database session
            agent1 = db.session.merge(self.agent1)
            
            analyzer = WorkloadAnalyzer()
            
            workload = analyzer.get_agent_current_workload(agent1.id)
            self.assertIsInstance(workload, (int, float))
            self.assertGreaterEqual(workload, 0)
    
    def test_assignment_analytics(self):
        """Test assignment analytics functionality."""
        with self.app.app_context():
            analytics = self.intelligent_assignment.get_assignment_analytics()
            
            self.assertIsInstance(analytics, dict)
            self.assertIn('total_assignments_today', analytics)
            self.assertIn('average_assignment_time', analytics)
            self.assertIn('strategy_usage', analytics)
            self.assertIn('agent_utilization', analytics)
    
    def test_error_handling_in_assignment(self):
        """Test error handling in assignment process."""
        with self.app.app_context():
            # Refresh service type from database session
            service_type = db.session.merge(self.service_type_passport)
            
            # Test with invalid service type
            with patch.object(self.intelligent_assignment, 'evaluate_agent_capability', 
                            side_effect=Exception("Test error")):
                result = self.intelligent_assignment.find_best_agent(
                    service_type, AssignmentStrategy.HYBRID
                )
                
                self.assertIsInstance(result, AssignmentResult)
                self.assertIsNone(result.agent_id)
                self.assertEqual(result.confidence_score, 0.0)
                self.assertIn('error', result.assignment_reason.lower())


if __name__ == '__main__':
    unittest.main()