#!/usr/bin/env python3
"""
Debug Tickets - Check actual database state for AGT001
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Agent, Queue, Citizen, ServiceType
        
        app = create_app()
        
        with app.app_context():
            print("🔍 DEBUGGING TICKET ASSIGNMENTS")
            print("=" * 50)
            
            # Find Marie Kouassi (AGT001)
            marie = Agent.query.filter_by(employee_id='AGT001').first()
            if not marie:
                print("❌ Marie Kouassi (AGT001) not found!")
                return
            
            print(f"👤 Found: {marie.first_name} {marie.last_name}")
            print(f"   ID: {marie.id}")
            print(f"   Employee ID: {marie.employee_id}")
            print(f"   Status: {marie.status}")
            print()
            
            # Check all tickets assigned to her
            print("🎫 ALL TICKETS ASSIGNED TO MARIE:")
            all_tickets = Queue.query.filter_by(agent_id=marie.id).all()
            print(f"Total tickets found: {len(all_tickets)}")
            
            for i, ticket in enumerate(all_tickets, 1):
                print(f"\n{i}. Ticket #{ticket.ticket_number}")
                print(f"   Database ID: {ticket.id}")
                print(f"   Status: {ticket.status}")
                print(f"   Agent ID: {ticket.agent_id}")
                print(f"   Citizen: {ticket.citizen.first_name} {ticket.citizen.last_name}")
                print(f"   Service: {ticket.service_type.name_fr if ticket.service_type else 'Unknown'}")
                print(f"   Priority: {ticket.priority_score}")
                print(f"   Created: {ticket.created_at}")
                print(f"   Updated: {ticket.updated_at}")
            
            # Check specifically waiting and in_progress tickets
            print("\n🔄 ACTIVE TICKETS (waiting + in_progress):")
            active_tickets = Queue.query.filter(
                Queue.agent_id == marie.id,
                Queue.status.in_(['waiting', 'in_progress'])
            ).all()
            
            print(f"Active tickets count: {len(active_tickets)}")
            for ticket in active_tickets:
                print(f"  - {ticket.ticket_number}: {ticket.status}")
            
            # Check what the agent dashboard query would return
            print("\n🖥️ AGENT DASHBOARD QUERY TEST:")
            dashboard_tickets = Queue.query.filter(
                Queue.agent_id == marie.id,
                Queue.status.in_(['waiting', 'in_progress'])
            ).join(Citizen).join(ServiceType).order_by(
                Queue.priority_score.desc(), Queue.created_at
            ).all()
            
            print(f"Dashboard query returns: {len(dashboard_tickets)} tickets")
            for ticket in dashboard_tickets:
                print(f"  - {ticket.ticket_number}: {ticket.status} (Priority: {ticket.priority_score})")
            
            # Check all tickets in system
            print("\n📊 SYSTEM OVERVIEW:")
            total_tickets = Queue.query.count()
            waiting_tickets = Queue.query.filter_by(status='waiting').count()
            in_progress_tickets = Queue.query.filter_by(status='in_progress').count()
            completed_tickets = Queue.query.filter_by(status='completed').count()
            
            print(f"Total tickets in system: {total_tickets}")
            print(f"Waiting: {waiting_tickets}")
            print(f"In Progress: {in_progress_tickets}")
            print(f"Completed: {completed_tickets}")
            
            # Show some waiting tickets for testing
            print("\n🎯 AVAILABLE TICKETS FOR TESTING:")
            unassigned_waiting = Queue.query.filter_by(
                status='waiting',
                agent_id=None
            ).limit(5).all()
            
            print(f"Unassigned waiting tickets: {len(unassigned_waiting)}")
            for ticket in unassigned_waiting:
                print(f"  - {ticket.ticket_number}: {ticket.citizen.first_name} {ticket.citizen.last_name}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
