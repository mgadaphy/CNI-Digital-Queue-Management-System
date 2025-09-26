#!/usr/bin/env python3
"""
Simple test for the optimization system using actual database schema
"""

import sys
import os
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, ServiceType, Citizen, Queue, Agent
from app.queue_logic.simple_optimizer import simple_optimizer

def create_simple_test_data():
    """Create minimal test data"""
    print("🔧 Creating simple test data...")
    
    # Create one service type
    service = ServiceType.query.filter_by(code='COLLECTION').first()
    if not service:
        service = ServiceType(
            code='COLLECTION',
            name_fr='Retrait de documents',
            name_en='Document Collection',
            description_fr='Retrait de documents CNI',
            description_en='CNI document collection',
            priority_level=3,
            estimated_duration=3,
            is_active=True
        )
        db.session.add(service)
    
    # Create one agent
    agent = Agent.query.filter_by(employee_id='TEST001').first()
    if not agent:
        agent = Agent(
            employee_id='TEST001',
            first_name='Test',
            last_name='Agent',
            email='test@example.com',
            status='available'
        )
        db.session.add(agent)
    
    # Create test citizens
    citizens_data = [
        {
            'first_name': 'Alice',
            'last_name': 'Normal',
            'date_of_birth': datetime(1985, 5, 15).date(),
            'pre_enrollment_code': 'TEST001',
            'preferred_language': 'fr',
            'special_needs': None
        },
        {
            'first_name': 'Bob',
            'last_name': 'Elderly',
            'date_of_birth': datetime(1945, 8, 22).date(),
            'pre_enrollment_code': 'TEST002',
            'preferred_language': 'en',
            'special_needs': 'elderly'
        }
    ]
    
    for citizen_data in citizens_data:
        existing = Citizen.query.filter_by(pre_enrollment_code=citizen_data['pre_enrollment_code']).first()
        if not existing:
            citizen = Citizen(**citizen_data)
            db.session.add(citizen)
    
    db.session.commit()
    print("✅ Simple test data created!")

def test_priority_calculation():
    """Test priority calculation with real data"""
    print("\n🧮 Testing Priority Calculation...")
    
    # Get test data
    service = ServiceType.query.filter_by(code='COLLECTION').first()
    normal_citizen = Citizen.query.filter_by(pre_enrollment_code='TEST001').first()
    elderly_citizen = Citizen.query.filter_by(pre_enrollment_code='TEST002').first()
    
    if not all([service, normal_citizen, elderly_citizen]):
        print("❌ Test data not found")
        return False
    
    # Test normal citizen
    normal_priority = simple_optimizer.priority_calculator.calculate_priority_score(
        normal_citizen, service, 10, {}  # 10 minutes wait, no special factors
    )
    
    # Test elderly citizen
    elderly_priority = simple_optimizer.priority_calculator.calculate_priority_score(
        elderly_citizen, service, 10, {'elderly': True}  # 10 minutes wait, elderly
    )
    
    print(f"  📊 Normal citizen priority: {normal_priority}")
    print(f"  📊 Elderly citizen priority: {elderly_priority}")
    print(f"  ✅ Elderly priority higher: {'YES' if elderly_priority > normal_priority else 'NO'}")
    
    return elderly_priority > normal_priority

def create_test_tickets():
    """Create test tickets"""
    print("\n🎫 Creating test tickets...")
    
    # Clear existing test tickets
    Queue.query.filter(Queue.ticket_number.like('SIMPLE%')).delete()
    db.session.commit()
    
    service = ServiceType.query.filter_by(code='COLLECTION').first()
    normal_citizen = Citizen.query.filter_by(pre_enrollment_code='TEST001').first()
    elderly_citizen = Citizen.query.filter_by(pre_enrollment_code='TEST002').first()
    
    if not all([service, normal_citizen, elderly_citizen]):
        print("❌ Test data not found")
        return []
    
    # Create tickets with different wait times
    tickets_data = [
        {
            'citizen': normal_citizen,
            'wait_minutes': 5,
            'ticket_number': 'SIMPLE001'
        },
        {
            'citizen': elderly_citizen,
            'wait_minutes': 10,
            'ticket_number': 'SIMPLE002'
        }
    ]
    
    tickets = []
    for ticket_data in tickets_data:
        # Calculate priority
        special_factors = {}
        if ticket_data['citizen'].special_needs and 'elderly' in ticket_data['citizen'].special_needs:
            special_factors['elderly'] = True
        
        priority = simple_optimizer.priority_calculator.calculate_priority_score(
            ticket_data['citizen'], service, ticket_data['wait_minutes'], special_factors
        )
        
        # Create ticket
        created_at = datetime.utcnow() - timedelta(minutes=ticket_data['wait_minutes'])
        ticket = Queue(
            ticket_number=ticket_data['ticket_number'],
            citizen_id=ticket_data['citizen'].id,
            service_type_id=service.id,
            status='waiting',
            priority_score=priority,
            created_at=created_at
        )
        
        db.session.add(ticket)
        tickets.append(ticket)
        
        print(f"  🎫 Created {ticket.ticket_number}: {ticket_data['citizen'].first_name} - Priority: {priority}")
    
    db.session.commit()
    return tickets

def test_optimization():
    """Test the optimization system"""
    print("\n🔄 Testing Queue Optimization...")
    
    # Get tickets before optimization
    tickets_before = Queue.query.filter(Queue.ticket_number.like('SIMPLE%')).all()
    print(f"  📋 Tickets before: {len(tickets_before)}")
    
    for ticket in tickets_before:
        print(f"     {ticket.ticket_number}: Priority {ticket.priority_score}")
    
    # Run optimization
    result = simple_optimizer.optimize_queue()
    
    print(f"\n  🔄 Optimization result:")
    print(f"     Success: {result.success}")
    print(f"     Message: {result.message}")
    print(f"     Optimized: {result.optimized_count}/{result.total_tickets}")
    
    # Get tickets after optimization
    tickets_after = Queue.query.filter(Queue.ticket_number.like('SIMPLE%')).order_by(Queue.priority_score.desc()).all()
    print(f"\n  📋 Tickets after (by priority):")
    
    for ticket in tickets_after:
        citizen_name = f"{ticket.citizen.first_name} {ticket.citizen.last_name}"
        print(f"     {ticket.ticket_number}: {citizen_name} - Priority: {ticket.priority_score}")
    
    return result.success

def run_simple_test():
    """Run simple test"""
    print("🚀 Running Simple Optimization Test")
    print("=" * 50)
    
    try:
        # Create test data
        create_simple_test_data()
        
        # Test priority calculation
        priority_test = test_priority_calculation()
        
        # Create test tickets
        tickets = create_test_tickets()
        
        # Test optimization
        optimization_test = test_optimization()
        
        # Summary
        print("\n🎉 Test Summary:")
        print(f"  ✅ Priority calculation: {'PASS' if priority_test else 'FAIL'}")
        print(f"  ✅ Ticket creation: {len(tickets)} tickets created")
        print(f"  ✅ Optimization: {'PASS' if optimization_test else 'FAIL'}")
        
        if priority_test and optimization_test:
            print("\n🏆 Simplified Optimization System: WORKING!")
        else:
            print("\n❌ Some tests failed")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        run_simple_test()
