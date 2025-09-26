import unittest
import json
from datetime import datetime
from app import create_app, db
from app.models import Citizen, Agent, ServiceType, Station
from app.utils.encryption import encryption
from app.schemas import CitizenSchema, AgentSchema, AgentCreateSchema
from marshmallow import ValidationError

class SecurityTestCase(unittest.TestCase):
    """Test security features and validation"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        db.create_all()
        
        # Create test data
        self.service_type = ServiceType(
            code='CNI001',
            name_fr='Carte Nationale d\'Identité',
            name_en='National Identity Card',
            description_fr='Service de délivrance de CNI',
            description_en='National ID card issuance service',
            priority_level=1,
            estimated_duration=30
        )
        
        self.station = Station(
            station_number='STA001',
            name='Station A',
            is_active=True
        )
        
        db.session.add(self.service_type)
        db.session.add(self.station)
        db.session.commit()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_data_encryption(self):
        """Test data encryption and decryption"""
        # Test basic encryption
        original_data = "sensitive information"
        encrypted = encryption.encrypt(original_data)
        decrypted = encryption.decrypt(encrypted)
        
        self.assertNotEqual(original_data, encrypted)
        self.assertEqual(original_data, decrypted)
    
    def test_phone_encryption(self):
        """Test phone number encryption"""
        phone = "1234567890"
        encrypted_phone = encryption.encrypt_phone(phone)
        decrypted_phone = encryption.decrypt_phone(encrypted_phone)
        
        self.assertNotEqual(phone, encrypted_phone)
        self.assertEqual("(123) 456-7890", decrypted_phone)
    
    def test_citizen_validation(self):
        """Test Citizen schema validation"""
        schema = CitizenSchema()
        
        # Valid data
        valid_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone_number': '+1234567890',
            'email': 'test@example.com',
            'pre_enrollment_code': 'ABC123456',
            'date_of_birth': '1990-01-01'
        }
        
        result = schema.load(valid_data)
        self.assertEqual(result.first_name, 'John')
        
        # Invalid data - missing required fields
        invalid_data = {
            'first_name': 'John'
        }
        
        with self.assertRaises(ValidationError):
            schema.load(invalid_data)
        
        invalid_phone_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': 'invalid-phone',
            'email': 'invalid-email',
            'pre_enrollment_code': '123',
            'date_of_birth': '1990-01-01'
        }
        
        with self.assertRaises(ValidationError):
            schema.load(invalid_phone_data)
    
    def test_agent_validation(self):
        """Test Agent schema validation"""
        schema = AgentCreateSchema()
        
        # Valid data
        valid_data = {
            'employee_id': 'EMP001',
            'email': 'agent1@example.com',
            'first_name': 'Agent',
            'last_name': 'One',
            'phone': '1234567890',
            'password': 'SecurePass123',
            'specializations': [1, 2]
        }
        
        result = schema.load(valid_data)
        self.assertEqual(result['employee_id'], 'EMP001')
        
        # Invalid email format
        invalid_email_data = {
            'employee_id': 'EMP002',
            'email': 'invalid-email',
            'first_name': 'Agent',
            'last_name': 'One',
            'password': 'SecurePass123'
        }
        
        with self.assertRaises(ValidationError):
            schema.load(invalid_email_data)
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection"""
        # Create a citizen
        citizen = Citizen(
            first_name='John',
            last_name='Doe',
            phone_number='1234567890',
            email='john.doe@example.com',
            pre_enrollment_code='PRE123456',
            date_of_birth=datetime(1990, 1, 1).date()
        )
        db.session.add(citizen)
        db.session.commit()
        
        # Attempt SQL injection in search
        malicious_input = "'; DROP TABLE citizens; --"
        
        # This should not cause any issues due to SQLAlchemy's parameterized queries
        result = Citizen.query.filter(Citizen.first_name.like(f'%{malicious_input}%')).all()
        self.assertEqual(len(result), 0)
        
        # Verify the table still exists
        all_citizens = Citizen.query.all()
        self.assertEqual(len(all_citizens), 1)
    
    def test_xss_protection(self):
        """Test XSS protection in data validation"""
        schema = CitizenSchema()
        
        xss_data = {
            'first_name': '<script>alert("XSS")</script>',
            'last_name': 'Test',
            'phone_number': '+1234567890',
            'email': 'test@example.com',
            'pre_enrollment_code': 'XSS123456',
            'date_of_birth': '1990-01-01'
        }
        
        # The schema should validate and sanitize the input
        result = schema.load(xss_data)
        # The script tag should be treated as regular text
        self.assertIn('script', result.first_name)
    
    def test_password_security(self):
        """Test password hashing and verification"""
        agent = Agent(
            employee_id='EMP001',
            email='test@example.com',
            first_name='Test',
            last_name='Agent'
        )
        
        password = 'securepassword123'
        agent.set_password(password)
        
        # Password should be hashed
        self.assertNotEqual(agent.password_hash, password)
        
        # Verification should work
        self.assertTrue(agent.check_password(password))
        self.assertFalse(agent.check_password('wrongpassword'))

if __name__ == '__main__':
    unittest.main()