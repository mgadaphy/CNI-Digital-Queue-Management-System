from .base import BaseTestCase
from src.app.models import Agent, Citizen, ServiceType, Queue
from src.app.extensions import db

class ApiTestCase(BaseTestCase):
    def _get_auth_token(self):
        agent = Agent(employee_id='123', email='test@example.com', first_name='Test', last_name='User')
        agent.set_password('password')
        db.session.add(agent)
        db.session.commit()
        response = self.client.post('/auth/login', json={'email': 'test@example.com', 'password': 'password'})
        return response.get_json()['access_token']

    def test_check_in(self):
        token = self._get_auth_token()
        response = self.client.post('/api/check-in',
            headers={'Authorization': f'Bearer {token}'},
            json={'pre_enrollment_code': 'ABC-123'})
        self.assertEqual(response.status_code, 201)
        self.assertIn('ticket_number', response.get_json())

    def test_get_next_in_queue(self):
        # Setup: create an agent, a citizen, a service type, and a queue entry
        token = self._get_auth_token()
        st1 = ServiceType(id=1, code='S-1', name_fr='Test', name_en='Test', priority_level=1, estimated_duration=10)
        c1 = Citizen(id=1, pre_enrollment_code='P-1', first_name='Test', last_name='Citizen', date_of_birth='1990-01-01')
        db.session.add_all([st1, c1])
        db.session.commit()

        q1 = Queue(citizen_id=1, service_type_id=1, ticket_number='T1', priority_score=10)
        db.session.add(q1)
        db.session.commit()

        # Call the endpoint
        response = self.client.get('/api/queue/next', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['ticket_number'], 'T1')

        # Verify the queue entry was updated
        updated_q1 = Queue.query.get(1)
        self.assertEqual(updated_q1.status, 'called')
