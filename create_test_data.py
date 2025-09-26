import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app import create_app, db
from app.models import Agent, ServiceType, Station, Citizen
from datetime import datetime, date

def create_test_data(app):
    with app.app_context():
        print("Creating test data for CNI Digital Queue Management System...")
        
        # Create Service Types
        service_types = [
            {
                'code': 'NEW_APP',
                'name_fr': 'Nouvelle Demande CNI',
                'name_en': 'New CNI Application',
                'description_fr': 'Première demande de carte nationale d\'identité',
                'description_en': 'First-time national identity card application',
                'priority_level': 2,
                'estimated_duration': 15
            },
            {
                'code': 'RENEWAL',
                'name_fr': 'Renouvellement CNI',
                'name_en': 'CNI Renewal',
                'description_fr': 'Renouvellement de carte nationale d\'identité expirée',
                'description_en': 'Renewal of expired national identity card',
                'priority_level': 2,
                'estimated_duration': 10
            },
            {
                'code': 'COLLECTION',
                'name_fr': 'Retrait CNI',
                'name_en': 'CNI Collection',
                'description_fr': 'Retrait de carte nationale d\'identité prête',
                'description_en': 'Collection of ready national identity card',
                'priority_level': 1,
                'estimated_duration': 5
            },
            {
                'code': 'CORRECTION',
                'name_fr': 'Correction CNI',
                'name_en': 'CNI Correction',
                'description_fr': 'Correction d\'informations sur la CNI',
                'description_en': 'Correction of information on CNI',
                'priority_level': 3,
                'estimated_duration': 20
            },
            {
                'code': 'EMERGENCY',
                'name_fr': 'Service d\'Urgence',
                'name_en': 'Emergency Service',
                'description_fr': 'Service d\'urgence pour cas exceptionnels',
                'description_en': 'Emergency service for exceptional cases',
                'priority_level': 1,
                'estimated_duration': 30
            }
        ]
        
        for service_data in service_types:
            existing = ServiceType.query.filter_by(code=service_data['code']).first()
            if not existing:
                service = ServiceType(**service_data)
                db.session.add(service)
                print(f"Created service type: {service_data['name_en']}")
        
        # Create Stations
        stations = [
            {
                'station_number': 'ST001',
                'name': 'Station Principale',
                'description': 'Station principale pour tous les services CNI',
                'supported_services': [1, 2, 3, 4, 5],  # All service types
                'location': 'Rez-de-chaussée',
                'status': 'available'
            },
            {
                'station_number': 'ST002',
                'name': 'Station Retraits',
                'description': 'Station dédiée aux retraits de CNI',
                'supported_services': [3],  # Collection only
                'location': 'Premier étage',
                'status': 'available'
            },
            {
                'station_number': 'ST003',
                'name': 'Station Urgences',
                'description': 'Station pour les services d\'urgence',
                'supported_services': [5],  # Emergency only
                'location': 'Rez-de-chaussée',
                'status': 'available'
            }
        ]
        
        for station_data in stations:
            existing = Station.query.filter_by(station_number=station_data['station_number']).first()
            if not existing:
                station = Station(**station_data)
                db.session.add(station)
                print(f"Created station: {station_data['name']}")
        
        # Create Test Citizens
        citizens = [
            {
                'pre_enrollment_code': 'TEST001',
                'first_name': 'Jean',
                'last_name': 'Dupont',
                'date_of_birth': date(1980, 5, 15),
                'phone_number': '0123456789',
                'email': 'jean.dupont@example.com',
                'preferred_language': 'fr',
                'special_needs': None
            },
            {
                'pre_enrollment_code': 'TEST002',
                'first_name': 'Marie',
                'last_name': 'Martin',
                'date_of_birth': date(1945, 8, 22),
                'phone_number': '0123456790',
                'email': 'marie.martin@example.com',
                'preferred_language': 'fr',
                'special_needs': 'elderly'
            },
            {
                'pre_enrollment_code': 'TEST003',
                'first_name': 'Ahmed',
                'last_name': 'Hassan',
                'date_of_birth': date(1990, 12, 3),
                'phone_number': '0123456791',
                'email': 'ahmed.hassan@example.com',
                'preferred_language': 'fr',
                'special_needs': 'disability'
            },
            {
                'pre_enrollment_code': 'TEST004',
                'first_name': 'Sophie',
                'last_name': 'Bernard',
                'date_of_birth': date(1985, 3, 10),
                'phone_number': '0123456792',
                'email': 'sophie.bernard@example.com',
                'preferred_language': 'fr',
                'special_needs': 'pregnant'
            },
            {
                'pre_enrollment_code': 'TEST005',
                'first_name': 'John',
                'last_name': 'Smith',
                'date_of_birth': date(1975, 7, 18),
                'phone_number': '0123456793',
                'email': 'john.smith@example.com',
                'preferred_language': 'en',
                'special_needs': None
            }
        ]
        
        for citizen_data in citizens:
            existing = Citizen.query.filter_by(pre_enrollment_code=citizen_data['pre_enrollment_code']).first()
            if not existing:
                citizen = Citizen(**citizen_data)
                db.session.add(citizen)
                print(f"Created citizen: {citizen_data['first_name']} {citizen_data['last_name']}")
        
        # Create Additional Agents
        agents = [
            {
                'employee_id': 'AGENT002',
                'first_name': 'Claire',
                'last_name': 'Dubois',
                'email': 'claire.dubois@cni.com',
                'role': 'agent',
                'status': 'available'
            },
            {
                'employee_id': 'AGENT003',
                'first_name': 'Pierre',
                'last_name': 'Moreau',
                'email': 'pierre.moreau@cni.com',
                'role': 'agent',
                'status': 'available'
            }
        ]
        
        for agent_data in agents:
            existing = Agent.query.filter_by(employee_id=agent_data['employee_id']).first()
            if not existing:
                agent = Agent(
                    employee_id=agent_data['employee_id'],
                    first_name=agent_data['first_name'],
                    last_name=agent_data['last_name'],
                    role=agent_data['role'],
                    status=agent_data['status']
                )
                agent.email = agent_data['email']
                agent.set_password('agent123')  # Same password for all test agents
                db.session.add(agent)
                print(f"Created agent: {agent_data['first_name']} {agent_data['last_name']} (Password: agent123)")
        
        db.session.commit()
        print("\n✅ Test data creation completed successfully!")
        print("\n📋 Summary:")
        print(f"- Service Types: {ServiceType.query.count()}")
        print(f"- Stations: {Station.query.count()}")
        print(f"- Citizens: {Citizen.query.count()}")
        print(f"- Agents: {Agent.query.count()}")
        
        print("\n🔑 Login Credentials:")
        print("Admin: ADMIN001 / admin123")
        print("Agent 1: AGENT001 / agent123")
        print("Agent 2: AGENT002 / agent123")
        print("Agent 3: AGENT003 / agent123")
        
        print("\n🎫 Test Citizens:")
        for citizen in citizens:
            print(f"- {citizen['first_name']} {citizen['last_name']}: {citizen['pre_enrollment_code']}")

if __name__ == '__main__':
    app = create_app()
    create_test_data(app)
