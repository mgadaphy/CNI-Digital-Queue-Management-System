#!/usr/bin/env python3
"""
Test Agent Dashboard - Debug the template rendering issue
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Queue, Agent, Citizen, ServiceType
        from sqlalchemy.orm import joinedload
        from sqlalchemy import desc
        
        app = create_app()
        
        with app.app_context():
            print("🔍 TESTING AGENT DASHBOARD QUERY")
            print("=" * 50)
            
            # Find Marie Kouassi
            marie = Agent.query.filter_by(employee_id='AGT001').first()
            if not marie:
                print("❌ Marie Kouassi not found!")
                return
            
            print(f"👤 Testing for: {marie.first_name} {marie.last_name} (ID: {marie.id})")
            
            # Test the exact query from agent dashboard
            print("\n🔍 TESTING DASHBOARD QUERY:")
            assigned_tickets = Queue.query.filter(
                Queue.agent_id == marie.id,
                Queue.status.in_(['waiting', 'in_progress'])
            ).join(Citizen).join(ServiceType).order_by(
                desc(Queue.priority_score), Queue.created_at
            ).all()
            
            print(f"Query returned: {len(assigned_tickets)} tickets")
            
            for i, ticket in enumerate(assigned_tickets, 1):
                print(f"\n{i}. Ticket {ticket.ticket_number}")
                print(f"   Status: {ticket.status}")
                print(f"   Agent ID: {ticket.agent_id}")
                print(f"   Citizen: {ticket.citizen.first_name} {ticket.citizen.last_name}")
                print(f"   Service: {ticket.service_type.name_fr if ticket.service_type else 'None'}")
                print(f"   Priority: {ticket.priority_score}")
                
                # Test template conditions
                print(f"   Template check - assigned_tickets exists: {bool(assigned_tickets)}")
                print(f"   Template check - len(assigned_tickets): {len(assigned_tickets)}")
            
            # Test with eager loading (like optimized queries)
            print("\n🔍 TESTING WITH EAGER LOADING:")
            eager_tickets = Queue.query.options(
                joinedload(Queue.citizen),
                joinedload(Queue.service_type)
            ).filter(
                Queue.agent_id == marie.id,
                Queue.status.in_(['waiting', 'in_progress'])
            ).order_by(
                desc(Queue.priority_score), Queue.created_at
            ).all()
            
            print(f"Eager loading returned: {len(eager_tickets)} tickets")
            
            # Test the boolean evaluation
            print(f"\n🔍 TEMPLATE BOOLEAN TESTS:")
            print(f"bool(assigned_tickets): {bool(assigned_tickets)}")
            print(f"assigned_tickets is not None: {assigned_tickets is not None}")
            print(f"len(assigned_tickets) > 0: {len(assigned_tickets) > 0}")
            
            # Create test tickets if none exist
            if len(assigned_tickets) == 0:
                print("\n🎫 CREATING TEST TICKET FOR MARIE:")
                
                # Get a citizen and service type
                citizen = Citizen.query.first()
                service_type = ServiceType.query.first()
                
                if citizen and service_type:
                    test_ticket = Queue(
                        ticket_number="TEST_MARIE_001",
                        citizen_id=citizen.id,
                        service_type_id=service_type.id,
                        agent_id=marie.id,
                        status='in_progress',
                        priority_score=500
                    )
                    
                    db.session.add(test_ticket)
                    db.session.commit()
                    
                    print(f"✅ Created test ticket: TEST_MARIE_001")
                    print("Now try refreshing Marie's dashboard!")
                else:
                    print("❌ No citizens or service types available for test ticket")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
