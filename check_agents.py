import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from app import create_app, db
from app.models import Agent
from werkzeug.security import check_password_hash

def check_agents(app):
    with app.app_context():
        print("🔍 Agent Database Analysis")
        print("=" * 50)
        
        # Get all agents
        agents = Agent.query.all()
        
        if not agents:
            print("❌ No agents found in database!")
            print("\n💡 Recommendation: Run 'python reset_agents.py' to create fresh agents")
            return
        
        print(f"📊 Total agents in database: {len(agents)}")
        print()
        
        # Analyze each agent
        for i, agent in enumerate(agents, 1):
            print(f"Agent {i}:")
            print(f"  🆔 ID: {agent.id}")
            print(f"  👤 Employee ID: {agent.employee_id}")
            print(f"  📛 Name: {agent.first_name} {agent.last_name}")
            print(f"  📧 Email: {agent.email}")
            print(f"  🎭 Role: {agent.role}")
            print(f"  📊 Status: {agent.status}")
            print(f"  ✅ Active: {agent.is_active}")
            print(f"  🔐 Has Password: {'Yes' if agent.password_hash else 'No'}")
            
            # Test password verification
            if agent.password_hash:
                test_passwords = ['admin123', 'agent123', 'password']
                password_works = None
                for pwd in test_passwords:
                    if check_password_hash(agent.password_hash, pwd):
                        password_works = pwd
                        break
                
                if password_works:
                    print(f"  🔑 Password: {password_works} ✅")
                else:
                    print(f"  🔑 Password: Unknown ❌")
            
            print()
        
        # Summary and recommendations
        print("📋 Summary:")
        admin_count = len([a for a in agents if a.role == 'admin'])
        agent_count = len([a for a in agents if a.role == 'agent'])
        available_count = len([a for a in agents if a.status == 'available'])
        
        print(f"  👑 Admins: {admin_count}")
        print(f"  👷 Agents: {agent_count}")
        print(f"  🟢 Available: {available_count}")
        
        # Check for specific agents
        print("\n🎯 Login Test Results:")
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
                    print(f"  ✅ {emp_id} / {password} - LOGIN WORKS")
                else:
                    print(f"  ❌ {emp_id} / {password} - INVALID PASSWORD")
            else:
                print(f"  ❌ {emp_id} - AGENT NOT FOUND")
        
        print("\n💡 Recommendations:")
        if admin_count == 0:
            print("  ⚠️  No admin users found - create at least one admin")
        if agent_count < 2:
            print("  ⚠️  Few agents available - consider creating more for testing")
        if available_count == 0:
            print("  ⚠️  No available agents - ticket assignment will fail")
        
        # Check for common issues
        issues = []
        for agent in agents:
            if not agent.password_hash:
                issues.append(f"Agent {agent.employee_id} has no password")
            if not agent.email:
                issues.append(f"Agent {agent.employee_id} has no email")
            if agent.status not in ['available', 'busy', 'offline', 'break']:
                issues.append(f"Agent {agent.employee_id} has invalid status: {agent.status}")
        
        if issues:
            print("\n⚠️  Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ No issues found with agent data")

if __name__ == '__main__':
    app = create_app()
    check_agents(app)
