#!/usr/bin/env python3
"""
Add Missing Agents - Creates the specific AGENT001, AGENT002, AGENT003 that the system expects
Run this from the root directory: python add_missing_agents.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent
        
        print("➕ Adding Missing AGENT001, AGENT002, AGENT003")
        print("=" * 50)
        
        # Create app with minimal config to avoid scheduler issues
        app = create_app()
        
        with app.app_context():
            # Check what agents we need to add
            needed_agents = [
                {
                    'employee_id': 'AGENT001',
                    'first_name': 'Agent',
                    'last_name': 'One',
                    'email': 'agent1@cni.com',
                    'role': 'agent',
                    'status': 'available',
                    'password': 'agent123'
                },
                {
                    'employee_id': 'AGENT002',
                    'first_name': 'Agent',
                    'last_name': 'Two',
                    'email': 'agent2@cni.com',
                    'role': 'agent',
                    'status': 'available',
                    'password': 'agent123'
                },
                {
                    'employee_id': 'AGENT003',
                    'first_name': 'Agent',
                    'last_name': 'Three',
                    'email': 'agent3@cni.com',
                    'role': 'agent',
                    'status': 'available',
                    'password': 'agent123'
                }
            ]
            
            added_count = 0
            
            for agent_data in needed_agents:
                # Check if agent already exists
                existing = Agent.query.filter_by(employee_id=agent_data['employee_id']).first()
                
                if existing:
                    print(f"  ✅ {agent_data['employee_id']} already exists")
                else:
                    try:
                        # Create new agent
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
                        print(f"  ➕ Created {agent_data['employee_id']} - {agent_data['first_name']} {agent_data['last_name']}")
                        added_count += 1
                        
                    except Exception as e:
                        print(f"  ❌ Error creating {agent_data['employee_id']}: {e}")
                        db.session.rollback()
                        return
            
            if added_count > 0:
                # Commit changes
                db.session.commit()
                print(f"\n✅ Successfully added {added_count} agents!")
            else:
                print(f"\n✅ All required agents already exist!")
            
            # Test login credentials
            print(f"\n🧪 Testing Login Credentials:")
            test_credentials = [
                ('ADMIN001', 'admin123'),
                ('AGENT001', 'agent123'),
                ('AGENT002', 'agent123'),
                ('AGENT003', 'agent123')
            ]
            
            from werkzeug.security import check_password_hash
            
            for emp_id, password in test_credentials:
                agent = Agent.query.filter_by(employee_id=emp_id).first()
                if agent and agent.password_hash and check_password_hash(agent.password_hash, password):
                    status_icon = "🟢" if agent.status == 'available' else "🟡"
                    print(f"  {status_icon} {emp_id} / {password} - ✅ LOGIN WORKS")
                elif agent:
                    print(f"  🔴 {emp_id} / {password} - ❌ WRONG PASSWORD")
                else:
                    print(f"  ⚪ {emp_id} - ❌ NOT FOUND")
            
            print(f"\n🎯 You can now login with:")
            print(f"  Admin: ADMIN001 / admin123")
            print(f"  Agent: AGENT001 / agent123")
            print(f"  Agent: AGENT002 / agent123")
            print(f"  Agent: AGENT003 / agent123")
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
