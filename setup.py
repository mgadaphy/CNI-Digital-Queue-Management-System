import os
import sys

# Add src to Python Path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, 'src'))

try:
    from src.app import create_app
    from src.app.extensions import db
    from src.app.models import Agent, ServiceType, SystemConfig
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
            print("Creating default admin account (ADMIN001)...")
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
        else:
            print("Admin account already exists.")

        # 2. Initialize Default Agent
        agent = Agent.query.filter_by(employee_id='AGT001').first()
        if not agent:
            print("Creating default agent account (AGT001)...")
            agent = Agent(
                employee_id='AGT001',
                first_name='Marie',
                last_name='Kouassi',
                email='marie@cni.gov',
                role='agent',
                is_active=True,
                status='available'
            )
            agent.set_password('agent123')
            db.session.add(agent)
        else:
            print("Default agent account already exists.")

        # 3. Initialize Default Services
        services = [
            {'code': 'NEW', 'name_fr': 'Nouvelle Demande', 'name_en': 'New Application', 'priority': 10, 'duration': 15},
            {'code': 'REN', 'name_fr': 'Renouvellement', 'name_en': 'Renewal', 'priority': 20, 'duration': 10},
            {'code': 'COL', 'name_fr': 'Retrait', 'name_en': 'Collection', 'priority': 30, 'duration': 5},
            {'code': 'LOST', 'name_fr': 'Perte/Vol', 'name_en': 'Lost/Stolen', 'priority': 40, 'duration': 20}
        ]
        
        for srv in services:
            service = ServiceType.query.filter_by(code=srv['code']).first()
            if not service:
                print(f"Creating missing default service: {srv['code']}")
                service = ServiceType(
                    code=srv['code'],
                    name_fr=srv['name_fr'],
                    name_en=srv['name_en'],
                    priority_level=srv['priority'],
                    estimated_duration=srv['duration'],
                    is_active=True
                )
                db.session.add(service)

        # 4. Initialize System Config
        config_auto = SystemConfig.query.filter_by(key='auto_assign_enabled').first()
        if not config_auto:
            print("Setting up default SystemConfig (auto_assign_enabled=true)...")
            config = SystemConfig(key='auto_assign_enabled', value='true')
            db.session.add(config)

        # Commit all changes
        db.session.commit()
        print("\nSetup complete! You can now run the app with: cd src && python run.py")

if __name__ == "__main__":
    setup_database()
