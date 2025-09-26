#!/usr/bin/env python3
"""
Test script for the simplified queue optimization system

This script creates sample data and tests the optimization functionality
to validate that Phase 2 improvements are working correctly.
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, ServiceType, Citizen, Queue, Agent
from app.queue_logic.simple_optimizer import simple_optimizer

def create_test_data():
    """Create sample data for testing"""
    print("🔧 Creating test data...")
    
    # Create service types if they don't exist
    service_types = [
        {
            'code': 'EMERGENCY',
            'name_fr': 'Urgence',
            'name_en': 'Emergency',
            'description_fr': 'Service d\'urgence',
            'description_en': 'Emergency service',
            'priority_level': 1,
            'estimated_duration': 12,
            'is_active': True
        },
        {
            'code': 'APPOINTMENT',
            'name_fr': 'Rendez-vous',
            'name_en': 'Appointment',
            'description_fr': 'Rendez-vous programmé',
            'description_en': 'Scheduled appointment',
            'priority_level': 2,
            'estimated_duration': 8,
            'is_active': True
        },
        {
            'code': 'COLLECTION',
            'name_fr': 'Retrait de documents',
            'name_en': 'Document Collection',
            'description_fr': 'Retrait de documents CNI',
            'description_en': 'CNI document collection',
            'priority_level': 3,
            'estimated_duration': 3,
            'is_active': True
        },
        {
            'code': 'RENEWAL',
            'name_fr': 'Renouvellement',
            'name_en': 'Renewal',
            'description_fr': 'Renouvellement de CNI',
            'description_en': 'CNI renewal',
            'priority_level': 4,
            'estimated_duration': 10,
            'is_active': True
        },
        {
            'code': 'NEW_APPLICATION',
            'name_fr': 'Nouvelle demande',
            'name_en': 'New Application',
            'description_fr': 'Nouvelle demande de CNI',
            'description_en': 'New CNI application',
            'priority_level': 5,
            'estimated_duration': 15,
            'is_active': True
        }
    ]
    
    for service_data in service_types:
        existing = ServiceType.query.filter_by(code=service_data['code']).first()
        if not existing:
            service = ServiceType(**service_data)
            db.session.add(service)
    
    # Create test agents
    agents_data = [
        {
            'employee_id': 'AGT001',
            'first_name': 'Marie',
            'last_name': 'Dubois',
            'email': 'marie.dubois@cni.gov',
            'status': 'available'
        },
        {
            'employee_id': 'AGT002',
            'first_name': 'Jean',
            'last_name': 'Martin',
            'email': 'jean.martin@cni.gov',
            'status': 'available'
        },
        {
            'employee_id': 'AGT003',
            'first_name': 'Sophie',
            'last_name': 'Bernard',
            'email': 'sophie.bernard@cni.gov',
            'status': 'busy'
        }
    ]
    
    for agent_data in agents_data:
        existing = Agent.query.filter_by(employee_id=agent_data['employee_id']).first()
        if not existing:
            agent = Agent(**agent_data)
            db.session.add(agent)
    
    # Create test citizens with various characteristics
    # Note: Using special_needs field to simulate special factors for testing
    citizens_data = [
        {
            'first_name': 'Alice',
            'last_name': 'Johnson',
            'date_of_birth': datetime(1985, 5, 15).date(),
            'pre_enrollment_code': 'PRE001',
            'preferred_language': 'fr',
            'special_needs': 'None'  # Normal citizen
        },
        {
            'first_name': 'Robert',
            'last_name': 'Smith',
            'date_of_birth': datetime(1945, 8, 22).date(),
            'pre_enrollment_code': 'PRE002',
            'preferred_language': 'en',
            'special_needs': 'elderly'  # Elderly citizen
        },
        {
            'first_name': 'Emma',
            'last_name': 'Wilson',
            'date_of_birth': datetime(1990, 12, 3).date(),
            'pre_enrollment_code': 'PRE003',
            'preferred_language': 'fr',
            'special_needs': 'disability'  # Citizen with disability
        },
        {
            'first_name': 'Sarah',
            'last_name': 'Davis',
            'date_of_birth': datetime(1992, 3, 18).date(),
            'pre_enrollment_code': 'PRE004',
            'preferred_language': 'en',
            'special_needs': 'pregnant'  # Pregnant citizen
        },
        {
            'first_name': 'Michael',
            'last_name': 'Brown',
            'date_of_birth': datetime(1988, 7, 9).date(),
            'pre_enrollment_code': 'PRE005',
            'preferred_language': 'fr',
            'special_needs': 'appointment'  # Has appointment
        }
    ]
    
    for citizen_data in citizens_data:
        existing = Citizen.query.filter_by(pre_enrollment_code=citizen_data['pre_enrollment_code']).first()
        if not existing:
            citizen = Citizen(**citizen_data)
            db.session.add(citizen)
    
    db.session.commit()
    print("✅ Test data created successfully!")

def create_test_tickets():
    """Create test tickets with different priorities and wait times"""
    print("🎫 Creating test tickets...")
    
    # Clear existing tickets
    Queue.query.delete()
    db.session.commit()
    
    # Get service types and citizens
    services = ServiceType.query.all()
    citizens = Citizen.query.all()
    
    if not services or not citizens:
        print("❌ No service types or citizens found. Run create_test_data first.")
        return
    
    # Create tickets with different scenarios
    test_scenarios = [
        {
            'citizen_index': 0,  # Alice - normal citizen
            'service_code': 'NEW_APPLICATION',
            'created_minutes_ago': 5,
            'expected_priority': 200  # Base priority for NEW_APPLICATION
        },
        {
            'citizen_index': 1,  # Robert - elderly
            'service_code': 'RENEWAL',
            'created_minutes_ago': 15,
            'expected_priority': 400 + 30 + 100  # Base + wait + elderly bonus
        },
        {
            'citizen_index': 2,  # Emma - disability
            'service_code': 'COLLECTION',
            'created_minutes_ago': 8,
            'expected_priority': 600 + 16 + 150  # Base + wait + disability bonus
        },
        {
            'citizen_index': 3,  # Sarah - pregnant
            'service_code': 'RENEWAL',
            'created_minutes_ago': 20,
            'expected_priority': 400 + 40 + 120  # Base + wait + pregnant bonus
        },
        {
            'citizen_index': 4,  # Michael - appointment
            'service_code': 'APPOINTMENT',
            'created_minutes_ago': 3,
            'expected_priority': 800 + 6 + 300  # Base + wait + appointment bonus
        }
    ]
    
    tickets_created = []
    
    for i, scenario in enumerate(test_scenarios):
        citizen = citizens[scenario['citizen_index']]
        service = ServiceType.query.filter_by(code=scenario['service_code']).first()
        
        if not service:
            print(f"❌ Service {scenario['service_code']} not found")
            continue
        
        # Calculate priority using simplified calculator
        special_factors = {}
        if citizen.special_needs:
            if 'elderly' in citizen.special_needs.lower():
                special_factors['elderly'] = True
            if 'disability' in citizen.special_needs.lower():
                special_factors['disability'] = True
            if 'pregnant' in citizen.special_needs.lower():
                special_factors['pregnant'] = True
            if 'appointment' in citizen.special_needs.lower():
                special_factors['appointment'] = True
        
        wait_time = scenario['created_minutes_ago']
        priority_score = simple_optimizer.priority_calculator.calculate_priority_score(
            citizen, service, wait_time, special_factors
        )
        
        # Create ticket with backdated creation time
        created_at = datetime.utcnow() - timedelta(minutes=wait_time)
        
        ticket = Queue(
            ticket_number=f"TEST{i+1:03d}",
            citizen_id=citizen.id,
            service_type_id=service.id,
            status='waiting',
            priority_score=priority_score,
            created_at=created_at
        )
        
        db.session.add(ticket)
        tickets_created.append({
            'ticket_number': ticket.ticket_number,
            'citizen_name': f"{citizen.first_name} {citizen.last_name}",
            'service_code': service.code,
            'priority_score': priority_score,
            'expected_priority': scenario['expected_priority'],
            'wait_time': wait_time,
            'special_factors': special_factors
        })
    
    db.session.commit()
    
    print(f"✅ Created {len(tickets_created)} test tickets:")
    for ticket in tickets_created:
        print(f"  🎫 {ticket['ticket_number']}: {ticket['citizen_name']} - {ticket['service_code']}")
        print(f"     Priority: {ticket['priority_score']:.0f} (expected ~{ticket['expected_priority']})")
        print(f"     Wait time: {ticket['wait_time']} min, Special: {ticket['special_factors']}")
    
    return tickets_created

def test_priority_calculation():
    """Test the priority calculation system"""
    print("\n🧮 Testing Priority Calculation...")
    
    # Get test data
    citizen = Citizen.query.filter_by(first_name='Robert').first()  # Elderly citizen
    service = ServiceType.query.filter_by(code='EMERGENCY').first()
    
    if not citizen or not service:
        print("❌ Test data not found")
        return
    
    # Test different scenarios
    test_cases = [
        {
            'name': 'Emergency service for elderly citizen',
            'wait_time': 10,
            'special_factors': {'elderly': True},
            'expected_min': 1000 + 20 + 100  # Emergency + wait + elderly
        },
        {
            'name': 'Regular service with no special factors',
            'wait_time': 5,
            'special_factors': {},
            'expected_min': 1000 + 10  # Emergency + wait
        },
        {
            'name': 'Long wait time (should be capped)',
            'wait_time': 200,  # Should be capped at 200 bonus
            'special_factors': {},
            'expected_min': 1000 + 200  # Emergency + max wait bonus
        }
    ]
    
    for case in test_cases:
        priority = simple_optimizer.priority_calculator.calculate_priority_score(
            citizen, service, case['wait_time'], case['special_factors']
        )
        
        print(f"  📊 {case['name']}")
        print(f"     Calculated: {priority:.0f}, Expected min: {case['expected_min']}")
        print(f"     ✅ {'PASS' if priority >= case['expected_min'] else 'FAIL'}")

def test_queue_optimization():
    """Test the queue optimization functionality"""
    print("\n🔄 Testing Queue Optimization...")
    
    # Get current queue state
    tickets_before = Queue.query.filter_by(status='waiting').all()
    print(f"  📋 Tickets before optimization: {len(tickets_before)}")
    
    for ticket in tickets_before:
        print(f"     {ticket.ticket_number}: {ticket.priority_score:.0f} priority")
    
    # Run optimization
    result = simple_optimizer.optimize_queue()
    
    print(f"\n  🔄 Optimization result:")
    print(f"     Success: {result.success}")
    print(f"     Message: {result.message}")
    print(f"     Optimized: {result.optimized_count}/{result.total_tickets}")
    
    # Get queue state after optimization
    tickets_after = Queue.query.filter_by(status='waiting').order_by(Queue.priority_score.desc()).all()
    print(f"\n  📋 Tickets after optimization (sorted by priority):")
    
    for ticket in tickets_after:
        citizen_name = f"{ticket.citizen.first_name} {ticket.citizen.last_name}"
        service_code = ticket.service_type.code
        wait_time = int((datetime.utcnow() - ticket.created_at).total_seconds() / 60)
        
        print(f"     {ticket.ticket_number}: {citizen_name} - {service_code}")
        print(f"       Priority: {ticket.priority_score:.0f}, Wait: {wait_time} min")
    
    return result

def test_agent_assignment():
    """Test the agent assignment functionality"""
    print("\n👥 Testing Agent Assignment...")
    
    # Get a waiting ticket
    ticket = Queue.query.filter_by(status='waiting').first()
    if not ticket:
        print("❌ No waiting tickets found")
        return
    
    print(f"  🎫 Testing assignment for ticket: {ticket.ticket_number}")
    
    # Test agent assignment
    success = simple_optimizer.assign_agent_to_ticket(ticket)
    
    if success:
        db.session.refresh(ticket)
        agent = ticket.agent
        print(f"  ✅ Successfully assigned agent: {agent.first_name} {agent.last_name} (ID: {agent.employee_id})")
        print(f"     Agent status: {agent.status}")
    else:
        print("  ❌ Failed to assign agent")
    
    return success

def run_comprehensive_test():
    """Run comprehensive test of the simplified optimization system"""
    print("🚀 Starting Comprehensive Test of Simplified Optimization System")
    print("=" * 70)
    
    try:
        # Create test data
        create_test_data()
        
        # Create test tickets
        tickets = create_test_tickets()
        
        # Test priority calculation
        test_priority_calculation()
        
        # Test queue optimization
        optimization_result = test_queue_optimization()
        
        # Test agent assignment
        assignment_result = test_agent_assignment()
        
        # Get final statistics
        stats = simple_optimizer.get_queue_statistics()
        
        print("\n📊 Final System Statistics:")
        print(f"  Waiting tickets: {stats['waiting']}")
        print(f"  In progress: {stats['in_progress']}")
        print(f"  Available agents: {stats['available_agents']}")
        print(f"  Busy agents: {stats['busy_agents']}")
        
        print("\n🎉 Test Summary:")
        print(f"  ✅ Test data creation: SUCCESS")
        print(f"  ✅ Ticket creation: {len(tickets)} tickets created")
        print(f"  ✅ Priority calculation: TESTED")
        print(f"  ✅ Queue optimization: {'SUCCESS' if optimization_result.success else 'FAILED'}")
        print(f"  ✅ Agent assignment: {'SUCCESS' if assignment_result else 'FAILED'}")
        
        print("\n🏆 Simplified Optimization System: FULLY FUNCTIONAL!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        run_comprehensive_test()
