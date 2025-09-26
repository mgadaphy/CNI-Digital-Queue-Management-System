#!/usr/bin/env python3
"""
Debug Script: Check Current Ticket Status in Database
This script shows what tickets exist and their current status values.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from app.models import db, Queue, Agent, Citizen, ServiceType

def debug_ticket_status():
    """Debug current ticket status in database"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 DEBUGGING TICKET STATUS IN DATABASE")
        print("=" * 50)
        
        # Get all tickets with agent assignments
        tickets_with_agents = Queue.query.filter(
            Queue.agent_id.isnot(None)
        ).join(Agent).join(Citizen).join(ServiceType).all()
        
        print(f"📊 Found {len(tickets_with_agents)} tickets with agent assignments")
        
        if not tickets_with_agents:
            print("❌ No tickets found with agent assignments!")
            return
        
        # Group by status
        status_counts = {}
        
        print(f"\n📋 TICKET DETAILS:")
        print("-" * 80)
        print(f"{'Ticket':<12} {'Agent':<15} {'Citizen':<20} {'Status':<12} {'Created':<10}")
        print("-" * 80)
        
        for ticket in tickets_with_agents:
            agent_name = f"{ticket.agent.first_name} {ticket.agent.last_name}"
            citizen_name = f"{ticket.citizen.first_name} {ticket.citizen.last_name}"
            created = ticket.created_at.strftime("%m/%d") if ticket.created_at else "N/A"
            
            print(f"{ticket.ticket_number:<12} {agent_name:<15} {citizen_name:<20} {ticket.status:<12} {created:<10}")
            
            # Count statuses
            status_counts[ticket.status] = status_counts.get(ticket.status, 0) + 1
        
        print("-" * 80)
        print(f"\n📊 STATUS SUMMARY:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count} tickets")
        
        # Check what the agent call_next function would find
        print(f"\n🔍 TESTING AGENT CALL_NEXT LOGIC:")
        
        # Get all agents
        agents = Agent.query.all()
        
        for agent in agents:
            print(f"\n👤 Agent: {agent.first_name} {agent.last_name} (ID: {agent.id})")
            
            # Test OLD logic (only 'assigned')
            old_logic_tickets = Queue.query.filter(
                Queue.agent_id == agent.id,
                Queue.status == 'assigned'
            ).all()
            
            # Test NEW logic (assigned + waiting)
            new_logic_tickets = Queue.query.filter(
                Queue.agent_id == agent.id,
                Queue.status.in_(['assigned', 'waiting'])
            ).all()
            
            # Test FULL logic (assigned + waiting + in_progress)
            full_logic_tickets = Queue.query.filter(
                Queue.agent_id == agent.id,
                Queue.status.in_(['assigned', 'waiting', 'in_progress'])
            ).all()
            
            print(f"  📋 Tickets found by different logic:")
            print(f"    - OLD (only 'assigned'): {len(old_logic_tickets)} tickets")
            print(f"    - NEW (assigned + waiting): {len(new_logic_tickets)} tickets")  
            print(f"    - FULL (assigned + waiting + in_progress): {len(full_logic_tickets)} tickets")
            
            if full_logic_tickets:
                print(f"  📝 Tickets this agent can call:")
                for ticket in full_logic_tickets:
                    print(f"    - #{ticket.ticket_number}: {ticket.status} (Priority: {ticket.priority_score})")

if __name__ == "__main__":
    try:
        debug_ticket_status()
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()
