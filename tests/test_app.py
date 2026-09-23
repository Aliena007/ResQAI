import os
import tempfile
import unittest
from unittest.mock import patch

from app import create_app, db


class ResQAITestCase(unittest.TestCase):
    def setUp(self):
        self.database_path = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
        os.environ['DATABASE_URL'] = f'sqlite:///{self.database_path}'
        os.environ['RESQAI_LLM_PROVIDER'] = 'fallback'
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.drop_all()
            db.engine.dispose()
        os.unlink(self.database_path)

    def register(self):
        return self.client.post('/auth/register', json={
            'username': 'student', 'email': 'student@example.com', 'password': 'secret123'
        })

    def test_health_and_browser_entry(self):
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_auth_and_incident_lifecycle(self):
        self.assertEqual(self.client.post('/incidents', json={'description': 'fire'}).status_code, 401)
        self.assertEqual(self.register().status_code, 201)
        response = self.client.post('/incidents', json={
            'description': 'Fire near the school', 'location': 'Central Road',
            'latitude': 12, 'longitude': 45,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['category'], 'fire')
        self.assertEqual(self.client.get('/incidents/1').get_json()['summary'], 'Fire near the school')
        self.assertEqual(self.client.patch('/incidents/1', json={'status': 'resolved'}).status_code, 200)

    def test_invalid_coordinates_are_rejected(self):
        self.register()
        response = self.client.post('/incidents', json={'description': 'flood', 'latitude': 100})
        self.assertEqual(response.status_code, 400)

    def test_weak_registration_is_rejected(self):
        response = self.client.post('/auth/register', json={
            'username': 'student', 'email': 'student@example.com', 'password': 'short'
        })
        self.assertEqual(response.status_code, 400)

    @patch('app.agent._weather_forecast')
    @patch('app.agent._geocode_location')
    def test_preventive_weather_agent_returns_risk_plan(self, geocode, forecast):
        geocode.return_value = {'name': 'Test City, Testland', 'latitude': 1.0, 'longitude': 2.0}
        forecast.return_value = {
            'timezone': 'UTC',
            'daily': {
                'time': ['2026-09-23'], 'weather_code': [95],
                'temperature_2m_max': [30], 'temperature_2m_min': [24],
                'precipitation_probability_max': [80], 'precipitation_sum': [35],
                'wind_speed_10m_max': [65],
            },
        }
        self.register()
        response = self.client.post('/weather/analyze', json={'location': 'Test City'})
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result['risk_level'], 'high')
        self.assertIn('thunderstorm', result['hazards'])
        self.assertTrue(result['recommended_actions'])


if __name__ == '__main__':
    unittest.main()
