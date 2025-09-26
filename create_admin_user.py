import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app import create_app, db
from app.models import Agent

def create_admin(app):
    with app.app_context():
        print("🔍 Checking existing agents in database...")
        
        # List all existing agents first
        existing_agents = Agent.query.all()
        print(f"Found {len(existing_agents)} existing agents:")
        for agent in existing_agents:
            print(f"  - {agent.employee_id}: {agent.first_name} {agent.last_name} ({agent.role})")
        
        # Check if admin already exists
        existing_admin = Agent.query.filter_by(employee_id='ADMIN001').first()
        if existing_admin:
            print("\n✅ Admin user (ADMIN001) already exists.")
            print(f"   Name: {existing_admin.first_name} {existing_admin.last_name}")
            print(f"   Email: {existing_admin.email}")
            print(f"   Status: {existing_admin.status}")
        else:
            try:
                admin = Agent(
                    employee_id='ADMIN001',
                    first_name='Admin',
                    last_name='User',
                    role='admin',
                    status='available',
                    is_active=True
                )
                # Set email using the property setter to handle encryption
                admin.email = 'admin@cni.com'
                admin.set_password('admin123')
                
                db.session.add(admin)
                db.session.commit()
                print("\n✅ Admin user created successfully.")
                print("   Credentials: ADMIN001 / admin123")
            except Exception as e:
                print(f"\n❌ Error creating admin: {str(e)}")
                db.session.rollback()

        # Check if test agent already exists
        existing_agent = Agent.query.filter_by(employee_id='AGENT001').first()
        if existing_agent:
            print("\n✅ Test agent (AGENT001) already exists.")
            print(f"   Name: {existing_agent.first_name} {existing_agent.last_name}")
            print(f"   Email: {existing_agent.email}")
            print(f"   Status: {existing_agent.status}")
        else:
            try:
                agent = Agent(
                    employee_id='AGENT001',
                    first_name='Test',
                    last_name='Agent',
                    role='agent',
                    status='available',  # Set agent as available for assignment
                    is_active=True
                )
                # Set email using the property setter to handle encryption
                agent.email = 'agent@cni.com'
                agent.set_password('agent123')
                
                db.session.add(agent)
                db.session.commit()
                print("\n✅ Test agent created successfully.")
                print("   Credentials: AGENT001 / agent123")
            except Exception as e:
                print(f"\n❌ Error creating agent: {str(e)}")
                db.session.rollback()
        
        # Final summary
        print(f"\n📊 Final agent count: {Agent.query.count()}")
        print("\n🔑 Available login credentials:")
        all_agents = Agent.query.all()
        for agent in all_agents:
            password = "admin123" if agent.role == "admin" else "agent123"
            print(f"   {agent.employee_id}: {password} ({agent.role})")

if __name__ == '__main__':
    app = create_app()
    create_admin(app)
