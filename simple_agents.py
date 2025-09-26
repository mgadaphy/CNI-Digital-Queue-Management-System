#!/usr/bin/env python3
"""
Simple Agent List - Just the essential login info
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent, Queue
        
        app = create_app()
        
        with app.app_context():
            print("🔑 AGENT LOGIN CREDENTIALS")
            print("=" * 40)
            
            agents = Agent.query.filter_by(is_active=True).all()
            
            for agent in agents:
                # Get ticket counts without causing errors
                try:
                    active_tickets = Queue.query.filter_by(
                        agent_id=agent.id,
                        status='in_progress'
                    ).count()
                except:
                    active_tickets = 0
                
                print(f"👤 {agent.first_name} {agent.last_name}")
                print(f"   Login ID: {agent.employee_id}")
                print(f"   Status: {agent.status}")
                print(f"   Active Tickets: {active_tickets}")
                print(f"   Default Password: agent123")
                print()
            
            # Highlight Marie specifically
            print("🎯 MARIE KOUASSI LOGIN:")
            print("   URL: http://127.0.0.1:5000/login")
            print("   Username: AGT001")
            print("   Password: agent123")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
