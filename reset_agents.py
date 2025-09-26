import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app import create_app, db
from app.models import Agent

def reset_agents(app):
    with app.app_context():
        print("🔄 Resetting Agent Management System...")
        
        # First, let's see what agents currently exist
        existing_agents = Agent.query.all()
        print(f"\n📊 Current agents in database: {len(existing_agents)}")
        for agent in existing_agents:
            print(f"  - ID: {agent.id}, Employee ID: {agent.employee_id}, Name: {agent.first_name} {agent.last_name}, Role: {agent.role}, Status: {agent.status}")
        
        # Ask user if they want to delete all existing agents
        print(f"\n⚠️  Found {len(existing_agents)} existing agents.")
        response = input("Do you want to DELETE ALL existing agents and create fresh ones? (yes/no): ").lower().strip()
        
        if response in ['yes', 'y']:
            # Delete all existing agents
            Agent.query.delete()
            db.session.commit()
            print("✅ All existing agents deleted.")
        else:
            print("❌ Operation cancelled. Existing agents preserved.")
            return
        
        # Create 4 new agents with proper structure
        agents_to_create = [
            {
                'employee_id': 'ADMIN001',
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@cni.com',
                'role': 'admin',
                'status': 'available',
                'password': 'admin123'
            },
            {
                'employee_id': 'AGENT001',
                'first_name': 'Marie',
                'last_name': 'Dubois',
                'email': 'marie.dubois@cni.com',
                'role': 'agent',
                'status': 'available',
                'password': 'agent123'
            },
            {
                'employee_id': 'AGENT002',
                'first_name': 'Pierre',
                'last_name': 'Martin',
                'email': 'pierre.martin@cni.com',
                'role': 'agent',
                'status': 'available',
                'password': 'agent123'
            },
            {
                'employee_id': 'AGENT003',
                'first_name': 'Sophie',
                'last_name': 'Bernard',
                'email': 'sophie.bernard@cni.com',
                'role': 'agent',
                'status': 'available',
                'password': 'agent123'
            }
        ]
        
        print(f"\n🏗️  Creating {len(agents_to_create)} new agents...")
        
        for agent_data in agents_to_create:
            try:
                # Create agent instance
                agent = Agent(
                    employee_id=agent_data['employee_id'],
                    first_name=agent_data['first_name'],
                    last_name=agent_data['last_name'],
                    role=agent_data['role'],
                    status=agent_data['status'],
                    is_active=True
                )
                
                # Set email using property setter (handles encryption)
                agent.email = agent_data['email']
                
                # Set password
                agent.set_password(agent_data['password'])
                
                # Add to session
                db.session.add(agent)
                
                print(f"  ✅ Created: {agent_data['employee_id']} - {agent_data['first_name']} {agent_data['last_name']} ({agent_data['role']})")
                
            except Exception as e:
                print(f"  ❌ Error creating {agent_data['employee_id']}: {str(e)}")
                db.session.rollback()
                return
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"\n✅ Successfully created all {len(agents_to_create)} agents!")
        except Exception as e:
            print(f"\n❌ Error committing agents to database: {str(e)}")
            db.session.rollback()
            return
        
        # Verify creation
        print(f"\n🔍 Verification - Agents now in database:")
        new_agents = Agent.query.all()
        for agent in new_agents:
            print(f"  - ID: {agent.id}, Employee ID: {agent.employee_id}, Name: {agent.first_name} {agent.last_name}")
            print(f"    Role: {agent.role}, Status: {agent.status}, Active: {agent.is_active}")
            print(f"    Email: {agent.email}")
            print()
        
        print("🎯 Login Credentials:")
        print("  Admin:   ADMIN001 / admin123")
        print("  Agent 1: AGENT001 / agent123")
        print("  Agent 2: AGENT002 / agent123")
        print("  Agent 3: AGENT003 / agent123")
        
        print(f"\n✨ Agent management system reset complete!")
        print(f"   Total agents: {len(new_agents)}")
        print(f"   Admin users: {len([a for a in new_agents if a.role == 'admin'])}")
        print(f"   Agent users: {len([a for a in new_agents if a.role == 'agent'])}")

def list_agents_only(app):
    """Just list existing agents without making changes"""
    with app.app_context():
        print("📋 Current Agents in Database:")
        agents = Agent.query.all()
        if not agents:
            print("  No agents found in database.")
        else:
            for agent in agents:
                print(f"  - ID: {agent.id}")
                print(f"    Employee ID: {agent.employee_id}")
                print(f"    Name: {agent.first_name} {agent.last_name}")
                print(f"    Email: {agent.email}")
                print(f"    Role: {agent.role}")
                print(f"    Status: {agent.status}")
                print(f"    Active: {agent.is_active}")
                print()

if __name__ == '__main__':
    app = create_app()
    
    print("🏢 CNI Agent Management System")
    print("1. List existing agents")
    print("2. Reset all agents (delete and recreate)")
    
    choice = input("\nEnter your choice (1 or 2): ").strip()
    
    if choice == '1':
        list_agents_only(app)
    elif choice == '2':
        reset_agents(app)
    else:
        print("Invalid choice. Exiting.")
