#!/usr/bin/env python3
"""
Check Database Contents - See what's in the current SQLite database
"""

import os
import sys
import sqlite3

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def check_sqlite_directly():
    """Check SQLite database directly"""
    db_path = r'c:\Users\Gadaphy\Documents\Projects\CNI-Digital-Queue-Management-System\src\instance\cni_db.sqlite'
    
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found at: {db_path}")
        return
    
    print(f"📊 CHECKING SQLITE DATABASE")
    print(f"Database path: {db_path}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"📋 TABLES FOUND: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check agents
        print(f"\n👥 AGENTS:")
        cursor.execute("SELECT id, employee_id, first_name, last_name, status FROM agent;")
        agents = cursor.fetchall()
        for agent in agents:
            print(f"  - ID: {agent[0]}, Employee: {agent[1]}, Name: {agent[2]} {agent[3]}, Status: {agent[4]}")
        
        # Check citizens
        print(f"\n👤 CITIZENS:")
        cursor.execute("SELECT id, first_name, last_name, phone, email FROM citizen;")
        citizens = cursor.fetchall()
        for citizen in citizens:
            print(f"  - ID: {citizen[0]}, Name: {citizen[1]} {citizen[2]}, Phone: {citizen[3]}")
        
        # Check service types
        print(f"\n🏢 SERVICE TYPES:")
        cursor.execute("SELECT id, name_fr, name_en, estimated_duration FROM service_type;")
        services = cursor.fetchall()
        for service in services:
            print(f"  - ID: {service[0]}, FR: {service[1]}, EN: {service[2]}, Duration: {service[3]}min")
        
        # Check queue entries
        print(f"\n🎫 QUEUE ENTRIES:")
        cursor.execute("""
            SELECT q.id, q.ticket_number, q.status, q.agent_id, c.first_name, c.last_name, s.name_fr 
            FROM queue q 
            LEFT JOIN citizen c ON q.citizen_id = c.id 
            LEFT JOIN service_type s ON q.service_type_id = s.id
            ORDER BY q.created_at DESC;
        """)
        tickets = cursor.fetchall()
        for ticket in tickets:
            agent_info = f"Agent {ticket[3]}" if ticket[3] else "Unassigned"
            print(f"  - {ticket[1]}: {ticket[2]} ({agent_info}) - {ticket[4]} {ticket[5]} - {ticket[6]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking SQLite: {e}")

def check_with_flask():
    """Check database using Flask ORM"""
    try:
        from app import create_app, db
        from app.models import Queue, Agent, Citizen, ServiceType
        
        app = create_app()
        
        with app.app_context():
            print(f"\n🔍 FLASK ORM CHECK:")
            print("=" * 30)
            
            # Check agents
            agents = Agent.query.all()
            print(f"👥 Agents: {len(agents)}")
            for agent in agents:
                print(f"  - {agent.employee_id}: {agent.first_name} {agent.last_name} ({agent.status})")
            
            # Check tickets
            tickets = Queue.query.all()
            print(f"\n🎫 Queue entries: {len(tickets)}")
            for ticket in tickets:
                agent_info = f"Agent {ticket.agent_id}" if ticket.agent_id else "Unassigned"
                print(f"  - {ticket.ticket_number}: {ticket.status} ({agent_info})")
            
            # Check Marie's tickets specifically
            marie = Agent.query.filter_by(employee_id='AGT001').first()
            if marie:
                marie_tickets = Queue.query.filter_by(agent_id=marie.id).all()
                print(f"\n👤 Marie Kouassi's tickets: {len(marie_tickets)}")
                for ticket in marie_tickets:
                    print(f"  - {ticket.ticket_number}: {ticket.status}")
            
    except Exception as e:
        print(f"❌ Error with Flask ORM: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🔍 DATABASE INVESTIGATION")
    print("=" * 50)
    
    # Check SQLite directly first
    check_sqlite_directly()
    
    # Then check with Flask
    check_with_flask()

if __name__ == '__main__':
    main()
