#!/usr/bin/env python3
"""
Script to create sample data for the CNI Digital Queue Management System
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import ServiceType, Station, Agent, Citizen, Queue
from datetime import datetime, timedelta
import random

def create_sample_service_types():
    """Create sample service types"""
    service_types = [
        {
            'code': 'ID_CARD',
            'name_fr': 'Carte d\'identité nationale',
            'name_en': 'National ID Card',
            'description_fr': 'Demande ou renouvellement de carte d\'identité',
            'description_en': 'ID card application or renewal',
            'priority_level': 2,
            'estimated_duration': 15,
            'required_documents': ['birth_certificate', 'proof_of_residence']
        },
        {
            'code': 'PASSPORT',
            'name_fr': 'Passeport',
            'name_en': 'Passport',
            'description_fr': 'Demande ou renouvellement de passeport',
            'description_en': 'Passport application or renewal',
            'priority_level': 3,
            'estimated_duration': 25,
            'required_documents': ['birth_certificate', 'id_card', 'photos']
        },
        {
            'code': 'BIRTH_CERT',
            'name_fr': 'Acte de naissance',
            'name_en': 'Birth Certificate',
            'description_fr': 'Demande d\'acte de naissance',
            'description_en': 'Birth certificate request',
            'priority_level': 1,
            'estimated_duration': 10,
            'required_documents': ['parent_id', 'hospital_record']
        },
        {
            'code': 'MARRIAGE_CERT',
            'name_fr': 'Certificat de mariage',
            'name_en': 'Marriage Certificate',
            'description_fr': 'Demande de certificat de mariage',
            'description_en': 'Marriage certificate request',
            'priority_level': 2,
            'estimated_duration': 12,
            'required_documents': ['spouse_ids', 'witnesses']
        },
        {
            'code': 'RESIDENCE_PERMIT',
            'name_fr': 'Permis de résidence',
            'name_en': 'Residence Permit',
            'description_fr': 'Demande de permis de résidence',
            'description_en': 'Residence permit application',
            'priority_level': 4,
            'estimated_duration': 30,
            'required_documents': ['passport', 'employment_letter', 'housing_proof']
        }
    ]
    
    for service_data in service_types:
        service = ServiceType.query.filter_by(code=service_data['code']).first()
        if not service:
            service = ServiceType(**service_data)
            db.session.add(service)
    
    db.session.commit()
    print(f"Created {len(service_types)} service types")

def create_sample_stations():
    """Create sample stations"""
    stations = [
        {
            'station_number': 'ST001',
            'name': 'Station A - Documents civils',
            'description': 'Station pour cartes d\'identité et actes civils',
            'supported_services': [1, 3, 4],  # ID_CARD, BIRTH_CERT, MARRIAGE_CERT
            'location': 'Rez-de-chaussée, Aile Est'
        },
        {
            'station_number': 'ST002',
            'name': 'Station B - Passeports',
            'description': 'Station spécialisée pour les passeports',
            'supported_services': [2],  # PASSPORT
            'location': 'Premier étage, Bureau 101'
        },
        {
            'station_number': 'ST003',
            'name': 'Station C - Immigration',
            'description': 'Station pour permis de résidence et immigration',
            'supported_services': [5],  # RESIDENCE_PERMIT
            'location': 'Premier étage, Bureau 105'
        },
        {
            'station_number': 'ST004',
            'name': 'Station D - Services généraux',
            'description': 'Station polyvalente pour tous services',
            'supported_services': [1, 2, 3, 4, 5],  # All services
            'location': 'Rez-de-chaussée, Aile Ouest'
        }
    ]
    
    for station_data in stations:
        station = Station.query.filter_by(station_number=station_data['station_number']).first()
        if not station:
            station = Station(**station_data)
            db.session.add(station)
    
    db.session.commit()
    print(f"Created {len(stations)} stations")

def create_sample_agents():
    """Create sample agents"""
    agents = [
        {
            'employee_id': 'ADM001',
            'first_name': 'Admin',
            'last_name': 'User',
            'email': 'admin@cni.gov.ci',
            'phone': '+225 00 00 00 00 00',
            'specializations': [1, 2, 3, 4, 5],
            'current_station_id': 1,
            'status': 'available',
            'role': 'admin'
        },
        {
            'employee_id': 'AGT001',
            'first_name': 'Marie',
            'last_name': 'Kouassi',
            'email': 'marie.kouassi@cni.gov.ci',
            'phone': '+225 01 02 03 04 05',
            'specializations': [1, 3, 4],  # ID_CARD, BIRTH_CERT, MARRIAGE_CERT
            'current_station_id': 1,
            'status': 'available',
            'role': 'agent'
        },
        {
            'employee_id': 'AGT002',
            'first_name': 'Kofi',
            'last_name': 'Asante',
            'email': 'kofi.asante@cni.gov.ci',
            'phone': '+225 01 02 03 04 06',
            'specializations': [2],  # PASSPORT
            'current_station_id': 2,
            'status': 'available',
            'role': 'agent'
        },
        {
            'employee_id': 'AGT003',
            'first_name': 'Fatou',
            'last_name': 'Diallo',
            'email': 'fatou.diallo@cni.gov.ci',
            'phone': '+225 01 02 03 04 07',
            'specializations': [5],  # RESIDENCE_PERMIT
            'current_station_id': 3,
            'status': 'busy',
            'role': 'agent'
        },
        {
            'employee_id': 'AGT004',
            'first_name': 'Ibrahim',
            'last_name': 'Traore',
            'email': 'ibrahim.traore@cni.gov.ci',
            'phone': '+225 01 02 03 04 08',
            'specializations': [1, 2, 3, 4, 5],  # All services
            'current_station_id': 4,
            'status': 'available',
            'role': 'agent'
        },
        {
            'employee_id': 'AGT005',
            'first_name': 'Aminata',
            'last_name': 'Kone',
            'email': 'aminata.kone@cni.gov.ci',
            'phone': '+225 01 02 03 04 09',
            'specializations': [1, 3],  # ID_CARD, BIRTH_CERT
            'current_station_id': 1,
            'status': 'break',
            'role': 'agent'
        }
    ]
    
    for agent_data in agents:
        agent = Agent.query.filter_by(employee_id=agent_data['employee_id']).first()
        if not agent:
            agent = Agent(**agent_data)
            agent.set_password('agent123')  # Default password
            db.session.add(agent)
    
    db.session.commit()
    print(f"Created {len(agents)} agents")

def create_sample_citizens():
    """Create sample citizens"""
    citizens = [
        {
            'pre_enrollment_code': 'CIT001',
            'first_name': 'Aya',
            'last_name': 'Bamba',
            'date_of_birth': datetime(1990, 5, 15).date(),
            'phone_number': '+225 07 08 09 10 11',
            'email': 'aya.bamba@email.com',
            'preferred_language': 'fr'
        },
        {
            'pre_enrollment_code': 'CIT002',
            'first_name': 'Kwame',
            'last_name': 'Nkrumah',
            'date_of_birth': datetime(1985, 8, 22).date(),
            'phone_number': '+225 07 08 09 10 12',
            'email': 'kwame.nkrumah@email.com',
            'preferred_language': 'en'
        },
        {
            'pre_enrollment_code': 'CIT003',
            'first_name': 'Aissata',
            'last_name': 'Camara',
            'date_of_birth': datetime(1992, 12, 3).date(),
            'phone_number': '+225 07 08 09 10 13',
            'email': 'aissata.camara@email.com',
            'preferred_language': 'fr',
            'special_needs': 'Wheelchair access required'
        },
        {
            'pre_enrollment_code': 'CIT004',
            'first_name': 'John',
            'last_name': 'Smith',
            'date_of_birth': datetime(1988, 3, 10).date(),
            'phone_number': '+225 07 08 09 10 14',
            'email': 'john.smith@email.com',
            'preferred_language': 'en'
        },
        {
            'pre_enrollment_code': 'CIT005',
            'first_name': 'Mariam',
            'last_name': 'Ouattara',
            'date_of_birth': datetime(1995, 7, 18).date(),
            'phone_number': '+225 07 08 09 10 15',
            'email': 'mariam.ouattara@email.com',
            'preferred_language': 'fr'
        },
        {
            'pre_enrollment_code': 'CIT006',
            'first_name': 'David',
            'last_name': 'Johnson',
            'date_of_birth': datetime(1987, 11, 25).date(),
            'phone_number': '+225 07 08 09 10 16',
            'email': 'david.johnson@email.com',
            'preferred_language': 'en'
        }
    ]
    
    for citizen_data in citizens:
        citizen = Citizen.query.filter_by(pre_enrollment_code=citizen_data['pre_enrollment_code']).first()
        if not citizen:
            citizen = Citizen(**citizen_data)
            db.session.add(citizen)
    
    db.session.commit()
    print(f"Created {len(citizens)} citizens")

def create_sample_queue_entries():
    """Create sample queue entries"""
    citizens = Citizen.query.all()
    service_types = ServiceType.query.all()
    agents = Agent.query.all()
    stations = Station.query.all()
    
    if not citizens or not service_types:
        print("No citizens or service types found. Cannot create queue entries.")
        return
    
    # Create some completed entries from yesterday
    yesterday = datetime.utcnow() - timedelta(days=1)
    
    # Create some current queue entries
    queue_entries = []
    
    # Completed entries from yesterday
    for i in range(8):
        citizen = random.choice(citizens)
        service_type = random.choice(service_types)
        agent = random.choice(agents)
        station = random.choice(stations)
        
        created_time = yesterday + timedelta(hours=random.randint(8, 16), minutes=random.randint(0, 59))
        called_time = created_time + timedelta(minutes=random.randint(5, 30))
        completed_time = called_time + timedelta(minutes=random.randint(10, 45))
        
        queue_entry = Queue(
            citizen_id=citizen.id,
            service_type_id=service_type.id,
            ticket_number=f"T{yesterday.strftime('%Y%m%d')}{i+1:03d}",
            status='completed',
            priority_score=random.randint(1, 10),
            created_at=created_time,
            called_at=called_time,
            completed_at=completed_time,
            wait_time=int((called_time - created_time).total_seconds() / 60),
            service_time=int((completed_time - called_time).total_seconds() / 60),
            agent_id=agent.id,
            station_id=station.id
        )
        queue_entries.append(queue_entry)
    
    # Current waiting entries
    today = datetime.utcnow()
    for i in range(5):
        citizen = random.choice(citizens)
        service_type = random.choice(service_types)
        
        created_time = today - timedelta(minutes=random.randint(10, 120))
        
        queue_entry = Queue(
            citizen_id=citizen.id,
            service_type_id=service_type.id,
            ticket_number=f"T{today.strftime('%Y%m%d')}{i+1:03d}",
            status='waiting',
            priority_score=random.randint(1, 10),
            created_at=created_time
        )
        queue_entries.append(queue_entry)
    
    # Current in-progress entries
    for i in range(2):
        citizen = random.choice(citizens)
        service_type = random.choice(service_types)
        agent = random.choice([a for a in agents if a.status in ['busy', 'available']])
        station = random.choice(stations)
        
        created_time = today - timedelta(minutes=random.randint(30, 90))
        called_time = today - timedelta(minutes=random.randint(5, 25))
        
        queue_entry = Queue(
            citizen_id=citizen.id,
            service_type_id=service_type.id,
            ticket_number=f"T{today.strftime('%Y%m%d')}{i+6:03d}",
            status='in_progress',
            priority_score=random.randint(1, 10),
            created_at=created_time,
            called_at=called_time,
            wait_time=int((called_time - created_time).total_seconds() / 60),
            agent_id=agent.id,
            station_id=station.id
        )
        queue_entries.append(queue_entry)
    
    for entry in queue_entries:
        existing = Queue.query.filter_by(ticket_number=entry.ticket_number).first()
        if not existing:
            db.session.add(entry)
    
    db.session.commit()
    print(f"Created {len(queue_entries)} queue entries")

def main():
    """Main function to create all sample data"""
    app = create_app()
    
    with app.app_context():
        print("Creating sample data for CNI Digital Queue Management System...")
        
        # Create tables if they don't exist
        db.create_all()
        
        # Create sample data
        create_sample_service_types()
        create_sample_stations()
        create_sample_agents()
        create_sample_citizens()
        create_sample_queue_entries()
        
        print("\nSample data creation completed successfully!")
        print("\nSample agent credentials:")
        print("- Employee ID: AGT001, Password: agent123")
        print("- Employee ID: AGT002, Password: agent123")
        print("- Employee ID: AGT003, Password: agent123")
        print("- Employee ID: AGT004, Password: agent123")
        print("- Employee ID: AGT005, Password: agent123")
        print("\nAdmin credentials:")
        print("- Employee ID: ADMIN001, Password: admin123")

if __name__ == '__main__':
    main()