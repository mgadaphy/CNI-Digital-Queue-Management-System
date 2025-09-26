#!/usr/bin/env python3
"""
Debug Ticket Assignment - Check agents and tickets status
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent, Queue, Citizen
        
        print("🔍 Debug Ticket Assignment")
        print("=" * 50)
        
        app = create_app()
        
        with app.app_context():
            # Check available agents
            print("📋 AGENTS STATUS:")
            agents = Agent.query.all()
            available_agents = []
            
            for agent in agents:
                print(f"  👤 {agent.first_name} {agent.last_name}")
                print(f"     Status: {agent.status}")
                print(f"     Active: {agent.is_active}")
                print(f"     Employee ID: {agent.employee_id}")
                
                if agent.status == 'available' and agent.is_active:
                    available_agents.append(agent)
                print()
            
            print(f"✅ Available agents for assignment: {len(available_agents)}")
            if available_agents:
                for agent in available_agents:
                    print(f"   - {agent.first_name} {agent.last_name} (ID: {agent.id})")
            print()
            
            # Check waiting tickets
            print("🎫 WAITING TICKETS:")
            waiting_tickets = Queue.query.filter_by(status='waiting').all()
            print(f"Total waiting tickets: {len(waiting_tickets)}")
            
            for i, ticket in enumerate(waiting_tickets[:5], 1):  # Show first 5
                print(f"  {i}. Ticket #{ticket.ticket_number}")
                print(f"     Status: {ticket.status}")
                print(f"     Citizen: {ticket.citizen.first_name} {ticket.citizen.last_name}")
                print(f"     Agent: {ticket.agent.first_name + ' ' + ticket.agent.last_name if ticket.agent else 'Unassigned'}")
                print()
            
            # Test assignment logic
            if available_agents and waiting_tickets:
                print("🧪 TESTING ASSIGNMENT LOGIC:")
                test_agent = available_agents[0]
                test_ticket = waiting_tickets[0]
                
                print(f"Test Agent: {test_agent.first_name} {test_agent.last_name}")
                print(f"  - Status: {test_agent.status}")
                print(f"  - Active: {test_agent.is_active}")
                print(f"  - Status in ['available', 'busy']: {test_agent.status in ['available', 'busy']}")
                
                print(f"Test Ticket: {test_ticket.ticket_number}")
                print(f"  - Status: {test_ticket.status}")
                print(f"  - Status in ['waiting', 'in_progress']: {test_ticket.status in ['waiting', 'in_progress']}")
                
                # Check current tickets for agent
                current_tickets = Queue.query.filter_by(
                    agent_id=test_agent.id, 
                    status='in_progress'
                ).count()
                print(f"  - Current tickets for agent: {current_tickets}")
                
            else:
                print("❌ Cannot test assignment - missing available agents or waiting tickets")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
