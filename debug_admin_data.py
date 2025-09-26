#!/usr/bin/env python3
"""
Debug Admin Dashboard Data - Check what data is being passed to the template
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    try:
        from app import create_app, db
        from app.utils.optimized_queries import QueryOptimizer
        
        print("🔍 Debug Admin Dashboard Data")
        print("=" * 50)
        
        app = create_app()
        
        with app.app_context():
            # Get dashboard data the same way admin route does
            dashboard_queries = QueryOptimizer()
            dashboard_data = dashboard_queries.get_dashboard_data()
            
            active_tickets = dashboard_data.get('recent_tickets', [])
            
            print(f"📊 Found {len(active_tickets)} active tickets:")
            print()
            
            for i, ticket in enumerate(active_tickets[:5], 1):  # Show first 5
                print(f"Ticket {i}:")
                print(f"  🎫 Number: {ticket.ticket_number}")
                print(f"  👤 Citizen: {ticket.citizen.first_name} {ticket.citizen.last_name}")
                print(f"  🆔 PE Code: {ticket.citizen.pre_enrollment_code}")
                print(f"  🏢 Service: {ticket.service_type.name_fr if ticket.service_type else 'None'}")
                print(f"  📊 Priority: {ticket.priority_score}")
                print(f"  📋 Status: {ticket.status}")
                print(f"  👷 Agent: {f'{ticket.agent.first_name} {ticket.agent.last_name}' if ticket.agent else 'Unassigned'}")
                print()
            
            # Check if any tickets are missing PE codes
            missing_pe_codes = [t for t in active_tickets if not t.citizen.pre_enrollment_code]
            if missing_pe_codes:
                print(f"⚠️  {len(missing_pe_codes)} tickets have missing PE codes:")
                for ticket in missing_pe_codes[:3]:
                    print(f"  - {ticket.ticket_number}: {ticket.citizen.first_name} {ticket.citizen.last_name}")
            else:
                print("✅ All tickets have PE codes")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
