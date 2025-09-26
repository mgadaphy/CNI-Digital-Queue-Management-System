#!/usr/bin/env python3
"""
Script to update service types to ID services and ensure proper data setup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, ServiceType
from datetime import datetime

def update_service_types():
    """Update service types to ID services"""
    app = create_app()
    
    with app.app_context():
        # Clear existing service types
        ServiceType.query.delete()
        
        # Create ID service types
        id_services = [
            {
                'code': 'NEW_APP',
                'name_fr': 'Nouvelle Demande',
                'name_en': 'New Application',
                'description_fr': 'Nouvelle demande de carte d\'identité nationale',
                'description_en': 'New national identity card application',
                'priority_level': 5,
                'estimated_duration': 15,
                'required_documents': ['birth_certificate', 'proof_of_residence', 'photos']
            },
            {
                'code': 'RENEWAL',
                'name_fr': 'Renouvellement',
                'name_en': 'Renewal',
                'description_fr': 'Renouvellement de carte d\'identité nationale',
                'description_en': 'National identity card renewal',
                'priority_level': 3,
                'estimated_duration': 10,
                'required_documents': ['old_id_card', 'photos']
            },
            {
                'code': 'COLLECTION',
                'name_fr': 'Retrait',
                'name_en': 'Collection',
                'description_fr': 'Retrait de carte d\'identité nationale',
                'description_en': 'National identity card collection',
                'priority_level': 2,
                'estimated_duration': 5,
                'required_documents': ['receipt', 'old_id_card']
            },
            {
                'code': 'CORRECTION',
                'name_fr': 'Correction',
                'name_en': 'Correction',
                'description_fr': 'Correction d\'informations sur carte d\'identité',
                'description_en': 'Identity card information correction',
                'priority_level': 7,
                'estimated_duration': 20,
                'required_documents': ['id_card', 'supporting_documents', 'correction_form']
            }
        ]
        
        for service_data in id_services:
            service = ServiceType(
                code=service_data['code'],
                name_fr=service_data['name_fr'],
                name_en=service_data['name_en'],
                description_fr=service_data['description_fr'],
                description_en=service_data['description_en'],
                priority_level=service_data['priority_level'],
                estimated_duration=service_data['estimated_duration'],
                required_documents=service_data['required_documents'],
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(service)
        
        db.session.commit()
        print("Service types updated successfully!")
        print(f"Added {len(id_services)} ID service types:")
        for service in id_services:
            print(f"  - {service['code']}: {service['name_en']}")

if __name__ == '__main__':
    update_service_types()