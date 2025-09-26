#!/usr/bin/env python3
"""
Quick Agent Reset - Simple script to reset all agents
Run this from the root directory: python quick_reset_agents.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent
        
        print("🔄 Quick Agent Reset")
        print("=" * 30)
        
        # Create app
        app = create_app()
        
        with app.app_context():
            # Show current agents
            existing_agents = Agent.query.all()
            print(f"Current agents: {len(existing_agents)}")
            for agent in existing_agents:
                print(f"  - {agent.employee_id}: {agent.first_name} {agent.last_name} ({agent.role})")
            
            # Confirm deletion
            if existing_agents:
                confirm = input(f"\n⚠️  Delete all {len(existing_agents)} agents and create fresh ones? (yes/no): ").lower().strip()
                if confirm not in ['yes', 'y']:
                    print("❌ Operation cancelled")
                    return
                
                # Delete all agents
                Agent.query.delete()
                db.session.commit()
                print("✅ All agents deleted")
            
            # Create 4 new agents
            agents_data = [
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
            
            print(f"\n🏗️  Creating {len(agents_data)} new agents...")
            
            for agent_data in agents_data:
                try:
                    agent = Agent(
                        employee_id=agent_data['employee_id'],
                        first_name=agent_data['first_name'],
                        last_name=agent_data['last_name'],
                        role=agent_data['role'],
                        status=agent_data['status'],
                        is_active=True
                    )
                    
                    # Set email and password
                    agent.email = agent_data['email']
                    agent.set_password(agent_data['password'])
                    
                    db.session.add(agent)
                    print(f"  ✅ {agent_data['employee_id']} - {agent_data['first_name']} {agent_data['last_name']}")
                    
                except Exception as e:
                    print(f"  ❌ Error creating {agent_data['employee_id']}: {e}")
                    db.session.rollback()
                    return
            
            # Commit all changes
            db.session.commit()
            print(f"\n✅ Successfully created all agents!")
            
            # Show login credentials
            print(f"\n🔑 Login Credentials:")
            print(f"  Admin:   ADMIN001 / admin123")
            print(f"  Agent 1: AGENT001 / agent123")
            print(f"  Agent 2: AGENT002 / agent123")
            print(f"  Agent 3: AGENT003 / agent123")
            
            print(f"\n🎯 Next steps:")
            print(f"  1. cd src")
            print(f"  2. python run.py")
            print(f"  3. Go to http://localhost:5000/auth/login")
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the root directory and have installed dependencies")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the database is initialized: cd src && flask db upgrade")

if __name__ == '__main__':
    main()
