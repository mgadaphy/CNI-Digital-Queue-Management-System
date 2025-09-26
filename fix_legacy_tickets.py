#!/usr/bin/env python3
"""
Database Migration Script: Fix Legacy Ticket Status
This script updates existing tickets to use the new status system.

Run this script to fix tickets that were assigned before the new 'assigned' status was implemented.
"""

import sys
import os
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from app.models import db, Queue, Agent

def fix_legacy_tickets():
    """Fix legacy tickets that have agent_id but wrong status"""
    
    app = create_app()
    
    with app.app_context():
        print("🔍 Scanning for legacy tickets that need status updates...")
        
        # Find tickets that have agent_id but are still 'waiting' or incorrectly 'in_progress'
        legacy_tickets = Queue.query.filter(
            Queue.agent_id.isnot(None),  # Has an agent assigned
            Queue.status.in_(['waiting', 'in_progress']),  # But has old status
            Queue.completed_at.is_(None)  # Not completed yet
        ).all()
        
        print(f"📊 Found {len(legacy_tickets)} legacy tickets to update")
        
        if not legacy_tickets:
            print("✅ No legacy tickets found. All tickets are using the new status system!")
            return
        
        # Show details of what will be updated
        print("\n📋 Tickets to be updated:")
        for ticket in legacy_tickets:
            agent_name = f"{ticket.agent.first_name} {ticket.agent.last_name}" if ticket.agent else "Unknown"
            print(f"  - Ticket #{ticket.ticket_number}: {ticket.status} → assigned (Agent: {agent_name})")
        
        # Ask for confirmation
        response = input(f"\n❓ Update {len(legacy_tickets)} tickets? (y/N): ").strip().lower()
        
        if response != 'y':
            print("❌ Migration cancelled by user")
            return
        
        # Update the tickets
        updated_count = 0
        for ticket in legacy_tickets:
            if ticket.status == 'waiting':
                # Tickets that are waiting but have an agent should be 'assigned'
                ticket.status = 'assigned'
                ticket.updated_at = datetime.utcnow()
                updated_count += 1
                print(f"  ✅ Updated ticket #{ticket.ticket_number}: waiting → assigned")
            
            elif ticket.status == 'in_progress' and not ticket.called_at:
                # Tickets that are 'in_progress' but never called should be 'assigned'
                ticket.status = 'assigned'
                ticket.updated_at = datetime.utcnow()
                updated_count += 1
                print(f"  ✅ Updated ticket #{ticket.ticket_number}: in_progress → assigned")
        
        # Commit changes
        try:
            db.session.commit()
            print(f"\n🎉 Successfully updated {updated_count} tickets!")
            print("✅ Legacy ticket migration completed successfully")
            
            # Show summary
            print(f"\n📊 Migration Summary:")
            print(f"  - Total tickets scanned: {len(legacy_tickets)}")
            print(f"  - Tickets updated: {updated_count}")
            print(f"  - New status workflow is now active")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {str(e)}")
            print("🔄 All changes have been rolled back")
            return False
        
        return True

def verify_migration():
    """Verify that the migration was successful"""
    
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Verifying migration results...")
        
        # Check for remaining legacy tickets
        remaining_legacy = Queue.query.filter(
            Queue.agent_id.isnot(None),
            Queue.status == 'waiting',
            Queue.completed_at.is_(None)
        ).count()
        
        # Check assigned tickets
        assigned_tickets = Queue.query.filter(
            Queue.status == 'assigned'
        ).count()
        
        print(f"📊 Verification Results:")
        print(f"  - Remaining legacy tickets: {remaining_legacy}")
        print(f"  - Tickets with 'assigned' status: {assigned_tickets}")
        
        if remaining_legacy == 0:
            print("✅ Migration verification successful!")
        else:
            print(f"⚠️  {remaining_legacy} legacy tickets still need attention")

if __name__ == "__main__":
    print("🚀 CNI Queue Management System - Legacy Ticket Status Migration")
    print("=" * 60)
    
    try:
        success = fix_legacy_tickets()
        if success:
            verify_migration()
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        sys.exit(1)
    
    print("\n🎯 Migration complete! Agents should now be able to call assigned citizens.")
