#!/usr/bin/env python3
"""
Quick Fix - Simple operations without complex imports
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
        
        app = create_app()
        
        with app.app_context():
            print("🔧 QUICK FIXES")
            print("=" * 30)
            
            # 1. Create simple test tickets
            print("1. Creating test tickets...")
            citizen = Citizen.query.first()
            service = ServiceType.query.first()
            
            if citizen and service:
                for i in range(3):
                    ticket = Queue(
                        ticket_number=f"QUICK{i+1:03d}",
                        citizen_id=citizen.id,
                        service_type_id=service.id,
                        status='waiting',
                        priority_score=500 + i*50
                    )
                    db.session.add(ticket)
                
                db.session.commit()
                print("✅ Created 3 test tickets")
            
            # 2. Show current state
            print("\n2. Current system state:")
            waiting = Queue.query.filter_by(status='waiting').count()
            in_progress = Queue.query.filter_by(status='in_progress').count()
            no_show = Queue.query.filter_by(status='no_show').count()
            
            print(f"   Waiting: {waiting}")
            print(f"   In Progress: {in_progress}")
            print(f"   No Show: {no_show}")
            
            print("\n✅ Done!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
