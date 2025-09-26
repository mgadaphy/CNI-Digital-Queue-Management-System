#!/usr/bin/env python3
"""
Debug Agent Tickets - Check what tickets are actually assigned to Marie Kouassi
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Queue, Agent, Citizen, ServiceType
        
        app = create_app()
        
        with app.app_context():
            print("🔍 DEBUGGING AGENT TICKETS")
            print("=" * 50)
            
            # Find Marie Kouassi
            marie = Agent.query.filter_by(employee_id='AGT001').first()
            if not marie:
                print("❌ Marie Kouassi not found!")
                return
            
            print(f"👤 Agent: {marie.first_name} {marie.last_name}")
            print(f"   ID: {marie.id}")
            print(f"   Employee ID: {marie.employee_id}")
            
            # Check all tickets in system
            print(f"\n📊 ALL TICKETS IN SYSTEM:")
            all_tickets = Queue.query.all()
            for ticket in all_tickets:
                agent_info = f"Agent {ticket.agent_id}" if ticket.agent_id else "Unassigned"
                print(f"  - {ticket.ticket_number}: {ticket.status} ({agent_info})")
            
            # Check tickets assigned to Marie specifically
            print(f"\n🎫 TICKETS ASSIGNED TO MARIE (Agent ID {marie.id}):")
            marie_tickets = Queue.query.filter_by(agent_id=marie.id).all()
            print(f"Found: {len(marie_tickets)} tickets")
            
            for ticket in marie_tickets:
                print(f"  - {ticket.ticket_number}: {ticket.status}")
            
            # Check waiting tickets that might be auto-assigned
            print(f"\n⏳ WAITING TICKETS (might be shown as 'next citizen'):")
            waiting_tickets = Queue.query.filter_by(status='waiting').all()
            print(f"Found: {len(waiting_tickets)} waiting tickets")
            
            for ticket in waiting_tickets:
                agent_info = f"Agent {ticket.agent_id}" if ticket.agent_id else "Unassigned"
                print(f"  - {ticket.ticket_number}: {agent_info}")
            
            # Test the exact query from agent dashboard
            print(f"\n🔍 TESTING AGENT DASHBOARD QUERY:")
            try:
                from sqlalchemy.orm import joinedload
                
                test_tickets = Queue.query.options(
                    joinedload(Queue.citizen),
                    joinedload(Queue.service_type)
                ).filter(
                    Queue.agent_id == marie.id,
                    Queue.status.in_(['waiting', 'in_progress'])
                ).all()
                
                print(f"Dashboard query result: {len(test_tickets)} tickets")
                for ticket in test_tickets:
                    print(f"  - {ticket.ticket_number}: {ticket.status} (Agent: {ticket.agent_id})")
                    
            except Exception as e:
                print(f"❌ Dashboard query failed: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
