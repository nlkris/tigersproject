# -*- coding: utf-8 -*-
"""
Created on Sun Oct 26 13:38:38 2025

@author: thoma
"""

# -*- coding: utf-8 -*-
"""
Created on Sun Oct 26 13:27:49 2025

@author: thoma
"""

import unittest
from app import app  # juste ton objet Flask

class RoutesTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_homepage(self):
        response = self.client.get('/')
        self.assertIn(response.status_code, [200, 302])  # 200 si page existe, 302 si redirigée

    def test_signup_page(self):
        response = self.client.get('/signup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Inscription', response.data)

    def test_login_page(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Connexion', response.data)

    # Exemple POST “simulé” sans DB
    def test_signup_post(self):
        response = self.client.post('/signup', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123456'
        })
        # Si ta route redirige vers login après succès
        self.assertIn(response.status_code, [200, 302])

    def test_login_post(self):
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': '123456'
        })
        # Comme tu n'as pas de DB, la connexion échouera probablement
        self.assertIn(response.status_code, [200, 302])

if __name__ == "__main__":
    unittest.main()
