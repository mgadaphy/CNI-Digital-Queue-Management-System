"""Tests for data encryption functionality"""

import unittest
from app import create_app
from app.models import Citizen, Agent
from app.extensions import db
from app.utils.encryption import encryption
from datetime import date

class TestEncryption(unittest.TestCase):
    """Test encryption functionality in models"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
    
    def tearDown(self):
        """Clean up test environment"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_citizen_phone_encryption(self):
        """Test that citizen phone numbers are encrypted and decrypted correctly"""
        # Create a citizen with phone number
        citizen = Citizen(
            pre_enrollment_code='TEST123456',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            phone_number='+1234567890'
        )
        
        # Check that the stored value is encrypted (different from original)
        assert citizen._phone_number != '(123) 456-7890'
        assert citizen._phone_number is not None
        
        # Check that the property returns the decrypted value
        assert citizen.phone_number == '(123) 456-7890'
    
    def test_citizen_email_encryption(self):
        """Test that citizen emails are encrypted and decrypted correctly"""
        # Create a citizen with email
        citizen = Citizen(
            pre_enrollment_code='TEST123456',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            email='john.doe@example.com'
        )
        
        # Check that the stored value is encrypted (different from original)
        assert citizen._email != 'john.doe@example.com'
        assert citizen._email is not None
        
        # Check that the property returns the decrypted value
        assert citizen.email == 'john.doe@example.com'
    
    def test_agent_email_encryption(self):
        """Test that agent emails are encrypted and decrypted correctly"""
        # Create an agent with email
        agent = Agent(
            employee_id='EMP001',
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com'
        )
        
        # Check that the stored value is encrypted (different from original)
        assert agent._email != 'jane.smith@example.com'
        assert agent._email is not None
        
        # Check that the property returns the decrypted value
        assert agent.email == 'jane.smith@example.com'
    
    def test_agent_phone_encryption(self):
        """Test that agent phone numbers are encrypted and decrypted correctly"""
        # Create an agent with phone
        agent = Agent(
            employee_id='EMP001',
            first_name='Jane',
            last_name='Smith',
            email='jane.smith@example.com',
            phone='+0987654321'
        )
        
        # Check that the stored value is encrypted (different from original)
        assert agent._phone != '(098) 765-4321'
        assert agent._phone is not None
        
        # Check that the property returns the decrypted value
        assert agent.phone == '(098) 765-4321'
    
    def test_null_values_handling(self):
        """Test that null values are handled correctly"""
        # Create citizen without phone and email
        citizen = Citizen(
            pre_enrollment_code='TEST123456',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1)
        )
        
        # Check that null values remain null
        assert citizen.phone_number is None
        assert citizen.email is None
        assert citizen._phone_number is None
        assert citizen._email is None
    
    def test_database_persistence(self):
        """Test that encrypted data persists correctly in database"""
        # Create and save a citizen
        citizen = Citizen(
            pre_enrollment_code='TEST123456',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            phone_number='+1234567890',
            email='john.doe@example.com'
        )
        
        db.session.add(citizen)
        db.session.commit()
        citizen_id = citizen.id
        
        # Clear session and reload from database
        db.session.expunge_all()
        reloaded_citizen = Citizen.query.get(citizen_id)
        
        # Check that data is correctly decrypted after reload
        assert reloaded_citizen.phone_number == '(123) 456-7890'
        assert reloaded_citizen.email == 'john.doe@example.com'
        
        # Check that stored values are still encrypted
        assert reloaded_citizen._phone_number != '(123) 456-7890'
        assert reloaded_citizen._email != 'john.doe@example.com'
        
        # Cleanup
        db.session.delete(reloaded_citizen)
        db.session.commit()
    
    def test_encryption_consistency(self):
        """Test that the same value decrypts consistently"""
        phone = '+1234567890'
        email = 'test@example.com'
        
        # Create two citizens with same data
        citizen1 = Citizen(
            pre_enrollment_code='TEST123456',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            phone_number=phone,
            email=email
        )
        
        citizen2 = Citizen(
            pre_enrollment_code='TEST789012',
            first_name='Jane',
            last_name='Smith',
            date_of_birth=date(1985, 5, 15),
            phone_number=phone,
            email=email
        )
        
        # Both should decrypt to the same values (formatted)
        assert citizen1.phone_number == '(123) 456-7890'
        assert citizen2.phone_number == '(123) 456-7890'
        assert citizen1.email == citizen2.email
        
        # Encrypted values may differ due to random salts/IVs, but decryption should be consistent
        assert citizen1._phone_number is not None
        assert citizen2._phone_number is not None
        assert citizen1._email is not None
        assert citizen2._email is not None

if __name__ == '__main__':
    unittest.main()