#!/usr/bin/env python3
"""
Pre-enrollment Code Generator Utility
Generates codes in format: PE-YYYYMMDD-XXXXXX
"""

import random
from datetime import datetime
from ..models import Citizen, db

def generate_pe_code(date=None):
    """
    Generate a Pre-enrollment code in format PE-YYYYMMDD-XXXXXX
    
    Args:
        date: datetime object, defaults to today
    
    Returns:
        str: Pre-enrollment code
    """
    if date is None:
        date = datetime.now()
    
    # Format: PE-YYYYMMDD-XXXXXX
    date_str = date.strftime('%Y%m%d')
    
    # Generate 6-digit counter (random for now, could be sequential)
    counter = random.randint(100000, 999999)
    
    return f"PE-{date_str}-{counter}"

def generate_unique_pe_code(date=None, max_attempts=100):
    """
    Generate a unique Pre-enrollment code that doesn't exist in database
    
    Args:
        date: datetime object, defaults to today
        max_attempts: maximum attempts to generate unique code
    
    Returns:
        str: Unique Pre-enrollment code
    """
    for _ in range(max_attempts):
        code = generate_pe_code(date)
        
        # Check if code already exists
        existing = Citizen.query.filter_by(pre_enrollment_code=code).first()
        if not existing:
            return code
    
    raise ValueError(f"Could not generate unique PE code after {max_attempts} attempts")

def update_existing_pe_codes():
    """
    Update existing citizens with incorrect PE code format
    """
    # Find citizens with PE codes that don't match the correct format
    citizens = Citizen.query.filter(
        Citizen.pre_enrollment_code.isnot(None),
        ~Citizen.pre_enrollment_code.like('PE-________-______')
    ).all()
    
    updated_count = 0
    
    for citizen in citizens:
        try:
            # Generate new PE code
            new_code = generate_unique_pe_code()
            old_code = citizen.pre_enrollment_code
            
            citizen.pre_enrollment_code = new_code
            db.session.add(citizen)
            
            print(f"Updated citizen {citizen.first_name} {citizen.last_name}: {old_code} -> {new_code}")
            updated_count += 1
            
        except Exception as e:
            print(f"Error updating citizen {citizen.id}: {e}")
            continue
    
    try:
        db.session.commit()
        print(f"Successfully updated {updated_count} citizens with new PE codes")
        return updated_count
    except Exception as e:
        db.session.rollback()
        print(f"Error committing changes: {e}")
        return 0

def validate_pe_code(code):
    """
    Validate if a PE code matches the correct format
    
    Args:
        code: str, PE code to validate
    
    Returns:
        bool: True if valid format
    """
    if not code or not isinstance(code, str):
        return False
    
    # Check format: PE-YYYYMMDD-XXXXXX
    parts = code.split('-')
    if len(parts) != 3:
        return False
    
    if parts[0] != 'PE':
        return False
    
    # Check date part (8 digits)
    if len(parts[1]) != 8 or not parts[1].isdigit():
        return False
    
    # Check counter part (6 digits)
    if len(parts[2]) != 6 or not parts[2].isdigit():
        return False
    
    return True