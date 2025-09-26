from .base import BaseTestCase
from src.app.models import Agent
from src.app.extensions import db

class AuthTestCase(BaseTestCase):
    def test_register(self):
        response = self.client.post('/auth/register',
            json={
                'employee_id': '123',
                'email': 'test@example.com',
                'password': 'password',
                'first_name': 'Test',
                'last_name': 'User'
            })
        self.assertEqual(response.status_code, 201)

    def test_login(self):
        agent = Agent(employee_id='123', email='test@example.com', first_name='Test', last_name='User')
        agent.set_password('password')
        db.session.add(agent)
        db.session.commit()

        response = self.client.post('/auth/login',
            json={'email': 'test@example.com', 'password': 'password'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.get_json())
