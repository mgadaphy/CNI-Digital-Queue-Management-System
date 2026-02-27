import os
import sys
from datetime import datetime, timedelta
import random

# Add src to Python Path
base_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from app import create_app
    from app.extensions import db
    from app.models import Agent, ServiceType, SystemConfig, Station, Citizen, Queue
except ImportError as e:
    print(f"Error importing app modules: {e}")
    print("Ensure you have run pip install -r requirements.txt and are running within the virtual environment.")
    sys.exit(1)

def setup_database():
    app = create_app()
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()

        # 1. Initialize Admin
        admin = Agent.query.filter_by(employee_id='ADMIN001').first()
        if not admin:
            print("Creating System Administrator (ADMIN001)...")
            admin = Agent(
                employee_id='ADMIN001',
                first_name='System',
                last_name='Administrator',
                email='admin@cni.gov',
                role='admin',
                is_active=True,
                status='available'
            )
            admin.set_password('admin123')
            db.session.add(admin)

        # 2. Initialize Default Agents
        agent1 = Agent.query.filter_by(employee_id='AGT001').first()
        if not agent1:
            print("Creating default Agent 1 (AGT001)...")
            agent1 = Agent(
                employee_id='AGT001',
                first_name='Marie',
                last_name='Kouassi',
                email='marie@cni.gov',
                role='agent',
                is_active=True,
                status='available'
            )
            agent1.set_password('agent123')
            db.session.add(agent1)

        agent2 = Agent.query.filter_by(employee_id='AGT002').first()
        if not agent2:
            print("Creating default Agent 2 (AGT002)...")
            agent2 = Agent(
                employee_id='AGT002',
                first_name='Jean',
                last_name='Bamba',
                email='jean@cni.gov',
                role='agent',
                is_active=True,
                status='available'
            )
            agent2.set_password('agent123')
            db.session.add(agent2)

        # 3. Initialize Default Services
        print("Initializing CNI Service Types...")
        services_data = [
            {'code': 'NEW', 'name_fr': 'Nouvelle Demande', 'name_en': 'New Application', 'priority': 10, 'duration': 15},
            {'code': 'REN', 'name_fr': 'Renouvellement', 'name_en': 'Renewal', 'priority': 20, 'duration': 10},
            {'code': 'COL', 'name_fr': 'Retrait', 'name_en': 'Collection', 'priority': 30, 'duration': 5},
            {'code': 'LOST', 'name_fr': 'Perte/Vol', 'name_en': 'Lost/Stolen', 'priority': 40, 'duration': 20}
        ]
        
        db_services = {}
        for srv in services_data:
            service = ServiceType.query.filter_by(code=srv['code']).first()
            if not service:
                service = ServiceType(
                    code=srv['code'],
                    name_fr=srv['name_fr'],
                    name_en=srv['name_en'],
                    priority_level=srv['priority'],
                    estimated_duration=srv['duration'],
                    is_active=True
                )
                db.session.add(service)
                db.session.commit()
            db_services[srv['code']] = service

        # 4. Initialize System Config
        print("Configuring System Preferences...")
        config_auto = SystemConfig.query.filter_by(key='auto_assign_enabled').first()
        if not config_auto:
            config = SystemConfig(key='auto_assign_enabled', value='true')
            db.session.add(config)

        # 5. Initialize Stations (Counters)
        print("Building Workstations (Counters)...")
        station1 = Station.query.filter_by(station_number='C01').first()
        if not station1:
            station1 = Station(station_number='C01', name='Counter 1 (Fast Track)', status='available', is_active=True)
            db.session.add(station1)
            
        station2 = Station.query.filter_by(station_number='C02').first()
        if not station2:
            station2 = Station(station_number='C02', name='Counter 2 (Standard)', status='available', is_active=True)
            db.session.add(station2)
            
        db.session.commit()

        # Try linking agents to stations
        if agent1 and not agent1.current_station_id:
            agent1.current_station_id = station1.id
        if agent2 and not agent2.current_station_id:
            agent2.current_station_id = station2.id

        # 6. Initialize Sample Citizens
        citizens_list = []
        if Citizen.query.count() == 0:
            print("Registering Sample Citizens...")
            samples = [
                ("Paul", "Kone", "1990-05-14", "PE-2023-0001", "22501020304"),
                ("Fatou", "Diallo", "1985-11-20", "PE-2023-0002", "22505060708"),
                ("Marc", "Aka", "2000-02-10", "PE-2023-0003", "22509101112"),
                ("Awa", "Toure", "1995-08-30", "PE-2023-0004", "22513141516")
            ]
            for fname, lname, dob_str, pe_code, phone in samples:
                cit = Citizen(
                    first_name=fname,
                    last_name=lname,
                    date_of_birth=datetime.strptime(dob_str, "%Y-%m-%d").date(),
                    pre_enrollment_code=pe_code,
                    preferred_language='en'
                )
                cit.phone_number = phone
                db.session.add(cit)
                citizens_list.append(cit)
            db.session.commit()
        else:
            citizens_list = Citizen.query.limit(4).all()

        # 7. Initialize Sample Queue Tickets (To make the dashboard look active)
        if Queue.query.count() == 0 and len(citizens_list) >= 4:
            print("Generating Sample Queue Traffic...")
            
            # Ticket 1: Waiting (Just arrived)
            q1 = Queue(
                citizen_id=citizens_list[0].id,
                service_type_id=db_services['NEW'].id,
                ticket_number='N-001',
                status='waiting',
                priority_score=10,
                created_at=datetime.utcnow() - timedelta(minutes=5)
            )
            
            # Ticket 2: Assigned (Agent assigned but hasn't started serving)
            q2 = Queue(
                citizen_id=citizens_list[1].id,
                service_type_id=db_services['REN'].id,
                ticket_number='R-001',
                status='assigned',
                priority_score=20,
                agent_id=agent1.id,
                created_at=datetime.utcnow() - timedelta(minutes=10)
            )
            
            # Ticket 3: In Progress (Currently at a counter)
            q3 = Queue(
                citizen_id=citizens_list[2].id,
                service_type_id=db_services['COL'].id,
                ticket_number='C-001',
                status='in_progress',
                priority_score=30,
                agent_id=agent2.id,
                station_id=station2.id,
                created_at=datetime.utcnow() - timedelta(minutes=20),
                called_at=datetime.utcnow() - timedelta(minutes=5)
            )
            
            # Ticket 4: Completed (Already finished today)
            q4 = Queue(
                citizen_id=citizens_list[3].id,
                service_type_id=db_services['LOST'].id,
                ticket_number='L-001',
                status='completed',
                priority_score=40,
                agent_id=agent1.id,
                station_id=station1.id,
                created_at=datetime.utcnow() - timedelta(minutes=60),
                called_at=datetime.utcnow() - timedelta(minutes=45),
                completed_at=datetime.utcnow() - timedelta(minutes=30),
                wait_time=15,
                service_time=15
            )
            
            db.session.add_all([q1, q2, q3, q4])
            db.session.commit()

        print("\n========================================================")
        print("Setup Complete! The project is fully seeded and ready.")
        print("========================================================\n")
        print("1. Admin Login:   ADMIN001 / admin123")
        print("2. Agent Login:   AGT001   / agent123")
        print("                  AGT002   / agent123")
        print("\nStart Server Command:")
        print("cd src && python run.py")

if __name__ == "__main__":
    setup_database()
