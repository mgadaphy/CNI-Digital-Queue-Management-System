#!/usr/bin/env python3
"""
Script to create a test citizen with enrollment code PE-20250703-100432
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Citizen
from datetime import datetime

def create_test_citizen():
    """Create test citizen with enrollment code PE-20250703-100432"""
    
    # Check if citizen already exists
    existing_citizen = Citizen.query.filter_by(pre_enrollment_code='PE-20250703-100432').first()
    if existing_citizen:
        print(f"Citizen with enrollment code PE-20250703-100432 already exists:")
        print(f"ID: {existing_citizen.id}")
        print(f"Name: {existing_citizen.first_name} {existing_citizen.last_name}")
        print(f"DOB: {existing_citizen.date_of_birth}")
        print(f"Phone: {existing_citizen.phone_number}")
        print(f"Email: {existing_citizen.email}")
        return existing_citizen
    
    # Create new test citizen
    test_citizen = Citizen(
        pre_enrollment_code='PE-20250703-100432',
        first_name='Jean',
        last_name='Kouame',
        date_of_birth=datetime(1985, 7, 3).date(),
        phone_number='+225 07 12 34 56 78',
        email='jean.kouame@example.com',
        preferred_language='fr',
        special_needs='None',
        is_active=True
    )
    
    try:
        db.session.add(test_citizen)
        db.session.commit()
        print(f"Successfully created test citizen:")
        print(f"ID: {test_citizen.id}")
        print(f"Enrollment Code: {test_citizen.pre_enrollment_code}")
        print(f"Name: {test_citizen.first_name} {test_citizen.last_name}")
        print(f"DOB: {test_citizen.date_of_birth}")
        print(f"Phone: {test_citizen.phone_number}")
        print(f"Email: {test_citizen.email}")
        return test_citizen
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating test citizen: {e}")
        return None

def list_existing_enrollment_codes():
    """List existing enrollment codes for testing"""
    print("\n=== Existing Enrollment Codes ===")
    citizens = Citizen.query.filter(Citizen.pre_enrollment_code.isnot(None)).all()
    
    if not citizens:
        print("No citizens with enrollment codes found.")
        return []
    
    codes = []
    for citizen in citizens:
        print(f"Code: {citizen.pre_enrollment_code} - {citizen.first_name} {citizen.last_name}")
        codes.append(citizen.pre_enrollment_code)
    
    return codes

def main():
    app = create_app()
    with app.app_context():
        print("Creating test citizen with enrollment code PE-20250703-100432...")
        citizen = create_test_citizen()
        
        print("\n" + "="*50)
        existing_codes = list_existing_enrollment_codes()
        
        print(f"\n=== Summary ===")
        print(f"Total citizens with enrollment codes: {len(existing_codes)}")
        print(f"Available codes for testing: {existing_codes}")
        
if __name__ == '__main__':
    main()