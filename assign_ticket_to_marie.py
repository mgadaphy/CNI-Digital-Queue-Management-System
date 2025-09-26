#!/usr/bin/env python3
"""
Assign Ticket to Marie - Simple database update to test agent dashboard
"""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Queue, Agent
        
        app = create_app()
        
        with app.app_context():
            print("🎯 ASSIGNING TICKET TO MARIE KOUASSI")
            print("=" * 40)
            
            # Find Marie Kouassi
            marie = Agent.query.filter_by(employee_id='AGT001').first()
            if not marie:
                print("❌ Marie Kouassi not found!")
                return
            
            print(f"👤 Found: {marie.first_name} {marie.last_name} (ID: {marie.id})")
            
            # Find QUICK003 ticket
            quick003 = Queue.query.filter_by(ticket_number='QUICK003').first()
            if not quick003:
                print("❌ QUICK003 ticket not found!")
                return
            
            print(f"🎫 Found ticket: {quick003.ticket_number} (Status: {quick003.status})")
            
            # Assign QUICK003 to Marie
            quick003.agent_id = marie.id
            quick003.status = 'waiting'  # Set to waiting so it shows in assigned tickets
            quick003.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            print(f"✅ Successfully assigned {quick003.ticket_number} to {marie.first_name} {marie.last_name}")
            print(f"   Status: {quick003.status}")
            print(f"   Agent ID: {quick003.agent_id}")
            
            # Verify the assignment
            marie_tickets = Queue.query.filter_by(agent_id=marie.id).all()
            print(f"\n📊 Marie's tickets after assignment: {len(marie_tickets)}")
            for ticket in marie_tickets:
                print(f"  - {ticket.ticket_number}: {ticket.status}")
            
            print("\n🎯 Now refresh the agent dashboard to see QUICK003 assigned to Marie!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
