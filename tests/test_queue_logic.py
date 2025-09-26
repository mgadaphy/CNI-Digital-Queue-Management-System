from .base import BaseTestCase
from src.app.models import Citizen, ServiceType, Queue
from src.app.queue_logic.optimizer import calculate_priority_score, get_next_citizen_in_queue
from src.app.extensions import db

class QueueLogicTestCase(BaseTestCase):
    def test_calculate_priority_score(self):
        citizen = Citizen(pre_enrollment_code='P-1', first_name='Test', last_name='Citizen', date_of_birth='1990-01-01')
        service_type = ServiceType(code='S-1', name_fr='Test Service', name_en='Test Service', priority_level=5, estimated_duration=10)
        score = calculate_priority_score(citizen, service_type)
        self.assertEqual(score, 50)

    def test_get_next_citizen(self):
        # Setup data
        st1 = ServiceType(id=1, code='S-1', name_fr='Low Prio', name_en='Low Prio', priority_level=1, estimated_duration=10)
        st2 = ServiceType(id=2, code='S-2', name_fr='High Prio', name_en='High Prio', priority_level=10, estimated_duration=10)
        c1 = Citizen(id=1, pre_enrollment_code='P-1', first_name='Low', last_name='Prio', date_of_birth='1990-01-01')
        c2 = Citizen(id=2, pre_enrollment_code='P-2', first_name='High', last_name='Prio', date_of_birth='1990-01-01')
        db.session.add_all([st1, st2, c1, c2])
        db.session.commit()

        q1 = Queue(citizen_id=1, service_type_id=1, ticket_number='T1', priority_score=10)
        q2 = Queue(citizen_id=2, service_type_id=2, ticket_number='T2', priority_score=100)
        db.session.add_all([q1, q2])
        db.session.commit()

        next_citizen_queue_entry = get_next_citizen_in_queue()
        self.assertIsNotNone(next_citizen_queue_entry)
        self.assertEqual(next_citizen_queue_entry.citizen_id, 2) # Should be the one with higher priority
