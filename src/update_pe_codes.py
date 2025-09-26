#!/usr/bin/env python3
"""
Script to update existing Pre-enrollment codes to correct format
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Citizen
from app.utils.pe_code_generator import update_existing_pe_codes, validate_pe_code

def main():
    app = create_app()
    with app.app_context():
        print("Updating Pre-enrollment codes to correct format...")
        print("Current format: PE-YYYYMMDD-XXXXXX")
        print("="*50)
        
        # Show current PE codes
        print("\nCurrent PE codes in database:")
        citizens = Citizen.query.filter(Citizen.pre_enrollment_code.isnot(None)).all()
        
        for citizen in citizens:
            code = citizen.pre_enrollment_code
            is_valid = validate_pe_code(code)
            status = "✓ Valid" if is_valid else "✗ Invalid"
            print(f"  {code} - {citizen.first_name} {citizen.last_name} [{status}]")
        
        print("\n" + "="*50)
        
        # Update invalid codes
        updated_count = update_existing_pe_codes()
        
        print("\n" + "="*50)
        print("\nUpdated PE codes:")
        
        # Show updated codes
        citizens = Citizen.query.filter(Citizen.pre_enrollment_code.isnot(None)).all()
        for citizen in citizens:
            code = citizen.pre_enrollment_code
            is_valid = validate_pe_code(code)
            status = "✓ Valid" if is_valid else "✗ Invalid"
            print(f"  {code} - {citizen.first_name} {citizen.last_name} [{status}]")
        
        print(f"\nSummary: Updated {updated_count} PE codes to correct format")

if __name__ == '__main__':
    main()