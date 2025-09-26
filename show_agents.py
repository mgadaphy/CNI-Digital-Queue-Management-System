#!/usr/bin/env python3
"""
Show All Agents - Display agent details including login credentials
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent
        
        print("👥 CNI Queue Management System - Agent Directory")
        print("=" * 60)
        
        app = create_app()
        
        with app.app_context():
            agents = Agent.query.all()
            
            if not agents:
                print("❌ No agents found in the system")
                return
            
            print(f"📊 Total Agents: {len(agents)}")
            print()
            
            for i, agent in enumerate(agents, 1):
                print(f"👤 Agent #{i}")
                print(f"   Name: {agent.first_name} {agent.last_name}")
                print(f"   Login ID: {agent.employee_id}")
                print(f"   Email: {agent.email if agent.email else 'Not set'}")
                print(f"   Phone: {agent.phone if agent.phone else 'Not set'}")
                print(f"   Status: {agent.status}")
                print(f"   Active: {'Yes' if agent.is_active else 'No'}")
                print(f"   Role: {agent.role}")
                print(f"   Station ID: {agent.current_station_id if agent.current_station_id else 'Not assigned'}")
                
                # Check if they have any active tickets
                from app.models import Queue
                active_tickets = Queue.query.filter_by(
                    agent_id=agent.id,
                    status='in_progress'
                ).count()
                
                waiting_tickets = Queue.query.filter_by(
                    agent_id=agent.id,
                    status='waiting'
                ).count()
                
                print(f"   Current Tickets: {active_tickets} in progress, {waiting_tickets} waiting")
                print(f"   Database ID: {agent.id}")
                print("-" * 50)
            
            # Show login instructions
            print("\n🔑 LOGIN INSTRUCTIONS:")
            print("To login as an agent:")
            print("1. Go to http://127.0.0.1:5000/login")
            print("2. Use the Employee ID as username")
            print("3. Default password is usually: agent123")
            print()
            
            # Highlight Marie Kouassi specifically
            marie = None
            for agent in agents:
                if agent.first_name.lower() == 'marie' and agent.last_name.lower() == 'kouassi':
                    marie = agent
                    break
            
            if marie:
                print("🎯 MARIE KOUASSI DETAILS:")
                print(f"   Login ID: {marie.employee_id}")
                print(f"   Status: {marie.status}")
                print(f"   Active: {'Yes' if marie.is_active else 'No'}")
                print(f"   Database ID: {marie.id}")
                print(f"   Login URL: http://127.0.0.1:5000/login")
                print(f"   Username: {marie.employee_id}")
                print(f"   Password: agent123 (default)")
            else:
                print("⚠️  Marie Kouassi not found in agent list")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
