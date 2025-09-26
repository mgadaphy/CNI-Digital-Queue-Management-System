#!/usr/bin/env python3
"""
Quick Agent Check - Simple script to check agents in the database
Run this from the root directory: python quick_agent_check.py
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent
        from werkzeug.security import check_password_hash
        
        print("🔍 Quick Agent Database Check")
        print("=" * 40)
        
        # Create app with minimal configuration
        app = create_app()
        
        with app.app_context():
            # Get all agents
            agents = Agent.query.all()
            
            if not agents:
                print("❌ No agents found in database!")
                print("\n💡 Run: python create_admin_user.py")
                return
            
            print(f"📊 Found {len(agents)} agents:")
            print()
            
            # Test login credentials
            test_credentials = [
                ('ADMIN001', 'admin123'),
                ('AGENT001', 'agent123'),
                ('AGENT002', 'agent123'),
                ('AGENT003', 'agent123')
            ]
            
            for emp_id, password in test_credentials:
                agent = Agent.query.filter_by(employee_id=emp_id).first()
                if agent:
                    if agent.password_hash and check_password_hash(agent.password_hash, password):
                        status_icon = "🟢" if agent.status == 'available' else "🟡"
                        print(f"  {status_icon} {emp_id} / {password} - ✅ LOGIN WORKS ({agent.role})")
                    else:
                        print(f"  🔴 {emp_id} / {password} - ❌ INVALID PASSWORD")
                else:
                    print(f"  ⚪ {emp_id} - ❌ NOT FOUND")
            
            print(f"\n📋 Summary:")
            admin_count = len([a for a in agents if a.role == 'admin'])
            agent_count = len([a for a in agents if a.role == 'agent'])
            available_count = len([a for a in agents if a.status == 'available'])
            
            print(f"  👑 Admins: {admin_count}")
            print(f"  👷 Agents: {agent_count}")
            print(f"  🟢 Available: {available_count}")
            
            if admin_count == 0:
                print("\n⚠️  No admin found - run: python create_admin_user.py")
            elif agent_count < 2:
                print("\n⚠️  Few agents - consider running: python reset_agents.py")
            else:
                print("\n✅ Agent system looks good!")
                
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the root directory and have installed dependencies")
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure the database is initialized: cd src && flask db upgrade")

if __name__ == '__main__':
    main()
