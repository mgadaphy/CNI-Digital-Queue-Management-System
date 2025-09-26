#!/usr/bin/env python3
"""
Fix No Show Tickets - Restore tickets that were incorrectly marked as no_show
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
            print("🔧 FIXING NO_SHOW TICKETS")
            print("=" * 40)
            
            # Find tickets marked as no_show that have agents assigned
            no_show_with_agents = Queue.query.filter(
                Queue.status == 'no_show',
                Queue.agent_id.isnot(None)
            ).all()
            
            print(f"Found {len(no_show_with_agents)} no_show tickets with agents assigned")
            
            fixed_count = 0
            for ticket in no_show_with_agents:
                agent = Agent.query.get(ticket.agent_id)
                agent_name = f"{agent.first_name} {agent.last_name}" if agent else "Unknown"
                
                print(f"\n🎫 Fixing ticket {ticket.ticket_number}")
                print(f"   Assigned to: {agent_name}")
                print(f"   Current status: {ticket.status}")
                
                # Restore to in_progress status since they were assigned
                ticket.status = 'in_progress'
                ticket.updated_at = datetime.utcnow()
                
                print(f"   ✅ Changed to: {ticket.status}")
                fixed_count += 1
            
            # Also check for any no_show tickets from Marie Kouassi specifically
            marie = Agent.query.filter_by(employee_id='AGT001').first()
            if marie:
                marie_no_show = Queue.query.filter(
                    Queue.status == 'no_show',
                    Queue.agent_id == marie.id
                ).all()
                
                print(f"\n👤 Marie Kouassi specific tickets marked as no_show: {len(marie_no_show)}")
                for ticket in marie_no_show:
                    print(f"   - {ticket.ticket_number}: Restoring to in_progress")
                    ticket.status = 'in_progress'
                    ticket.updated_at = datetime.utcnow()
            
            if fixed_count > 0:
                db.session.commit()
                print(f"\n✅ Successfully fixed {fixed_count} tickets!")
            else:
                print("\n✅ No tickets needed fixing")
            
            # Show current state
            print(f"\n📊 CURRENT SYSTEM STATE:")
            waiting = Queue.query.filter_by(status='waiting').count()
            in_progress = Queue.query.filter_by(status='in_progress').count()
            no_show = Queue.query.filter_by(status='no_show').count()
            completed = Queue.query.filter_by(status='completed').count()
            
            print(f"   Waiting: {waiting}")
            print(f"   In Progress: {in_progress}")
            print(f"   No Show: {no_show}")
            print(f"   Completed: {completed}")
            
            # Show Marie's tickets specifically
            if marie:
                marie_tickets = Queue.query.filter_by(agent_id=marie.id).all()
                print(f"\n👤 Marie Kouassi's tickets: {len(marie_tickets)}")
                for ticket in marie_tickets:
                    print(f"   - {ticket.ticket_number}: {ticket.status}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
