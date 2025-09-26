#!/usr/bin/env python3
"""
Create Test Tickets - Add new tickets for testing
"""

import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.models import Queue, Citizen, ServiceType
        from app.queue_logic.simple_optimizer import SimplePriorityCalculator
        
        app = create_app()
        
        with app.app_context():
            print("🎫 CREATING TEST TICKETS")
            print("=" * 40)
            
            # Get available citizens and service types
            citizens = Citizen.query.limit(5).all()
            service_types = ServiceType.query.limit(3).all()
            
            if not citizens:
                print("❌ No citizens found. Please create some citizens first.")
                return
                
            if not service_types:
                print("❌ No service types found. Please create some service types first.")
                return
            
            print(f"Found {len(citizens)} citizens and {len(service_types)} service types")
            
            # Create priority calculator
            priority_calc = SimplePriorityCalculator()
            
            # Create 5 test tickets
            tickets_created = 0
            for i, citizen in enumerate(citizens):
                service_type = service_types[i % len(service_types)]
                
                # Generate ticket number
                ticket_number = f"TEST{1000 + i}"
                
                # Calculate priority (fix method name)
                priority_score = priority_calc.calculate_priority_score(
                    service_type_id=service_type.id,
                    wait_time_minutes=0,
                    is_elderly=citizen.is_elderly,
                    is_disabled=citizen.is_disabled,
                    is_pregnant=citizen.is_pregnant
                )
                
                # Create ticket
                ticket = Queue(
                    ticket_number=ticket_number,
                    citizen_id=citizen.id,
                    service_type_id=service_type.id,
                    priority_score=priority_score,
                    status='waiting',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(ticket)
                tickets_created += 1
                
                print(f"✅ Created ticket {ticket_number}")
                print(f"   Citizen: {citizen.first_name} {citizen.last_name}")
                print(f"   Service: {service_type.name_fr}")
                print(f"   Priority: {priority_score}")
                print()
            
            db.session.commit()
            
            print(f"🎯 Successfully created {tickets_created} test tickets!")
            print("\nThese tickets are now available for assignment testing.")
            
            # Show current system state
            total_waiting = Queue.query.filter_by(status='waiting').count()
            total_in_progress = Queue.query.filter_by(status='in_progress').count()
            
            print(f"\n📊 Current System State:")
            print(f"   Waiting tickets: {total_waiting}")
            print(f"   In progress tickets: {total_in_progress}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
