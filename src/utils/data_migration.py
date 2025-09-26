"""Data migration utilities for encrypting existing sensitive data"""

from app.models import Citizen, Agent
from app.extensions import db
from app.utils.encryption import encryption
import logging

logger = logging.getLogger(__name__)

def migrate_citizen_data():
    """Migrate existing citizen data to encrypted format"""
    try:
        # Get all citizens with unencrypted data
        citizens = Citizen.query.all()
        
        for citizen in citizens:
            # Check if phone_number needs encryption (not already encrypted)
            if citizen._phone_number and len(citizen._phone_number) < 100:  # Assume unencrypted if short
                original_phone = citizen._phone_number
                citizen.phone_number = original_phone  # Use property setter to encrypt
                logger.info(f"Encrypted phone for citizen {citizen.id}")
            
            # Check if email needs encryption (not already encrypted)
            if citizen._email and len(citizen._email) < 100:  # Assume unencrypted if short
                original_email = citizen._email
                citizen.email = original_email  # Use property setter to encrypt
                logger.info(f"Encrypted email for citizen {citizen.id}")
        
        db.session.commit()
        logger.info("Successfully migrated citizen data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error migrating citizen data: {str(e)}")
        raise

def migrate_agent_data():
    """Migrate existing agent data to encrypted format"""
    try:
        # Get all agents with unencrypted data
        agents = Agent.query.all()
        
        for agent in agents:
            # Check if email needs encryption (not already encrypted)
            if agent._email and len(agent._email) < 100:  # Assume unencrypted if short
                original_email = agent._email
                agent.email = original_email  # Use property setter to encrypt
                logger.info(f"Encrypted email for agent {agent.id}")
            
            # Check if phone needs encryption (not already encrypted)
            if agent._phone and len(agent._phone) < 100:  # Assume unencrypted if short
                original_phone = agent._phone
                agent.phone = original_phone  # Use property setter to encrypt
                logger.info(f"Encrypted phone for agent {agent.id}")
        
        db.session.commit()
        logger.info("Successfully migrated agent data")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error migrating agent data: {str(e)}")
        raise

def migrate_all_data():
    """Migrate all existing sensitive data to encrypted format"""
    logger.info("Starting data migration for encryption")
    
    try:
        migrate_citizen_data()
        migrate_agent_data()
        logger.info("Data migration completed successfully")
        
    except Exception as e:
        logger.error(f"Data migration failed: {str(e)}")
        raise

if __name__ == '__main__':
    # Run migration when script is executed directly
    migrate_all_data()