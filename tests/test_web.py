"""Hardware-independent HTTP checks for the workbench's core workflow."""

import http.client
import importlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch


class WorkbenchHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Imports create application state, so use a private temporary directory.
        cls.temp = tempfile.TemporaryDirectory()
        with patch.object(Path, 'home', return_value=Path(cls.temp.name)):
            cls.backend = importlib.import_module('backend')
        cls.server = cls.backend.Server(('127.0.0.1', 0), cls.backend.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def authenticated_headers(self):
        return {'Cookie': 'pi_workbench=' + self.backend.TOKEN}

    def test_login_and_protected_page(self):
        status, _, page = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'name="token"', page)
        status, _, _ = self.request('GET', '/api/tasks')
        self.assertEqual(status, 401)
        status, _, _ = self.request('GET', '/api/tasks', headers={'Cookie': 'pi_workbench=invalid'})
        self.assertEqual(status, 401)

        status, headers, _ = self.request('GET', '/?token=' + self.backend.TOKEN)
        self.assertEqual(status, 303)
        self.assertEqual(headers['Location'], '/')
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', headers['Set-Cookie'])
        status, _, page = self.request('GET', '/', headers=self.authenticated_headers())
        self.assertEqual(status, 200)
        self.assertEqual(page, (self.backend.ROOT / 'index.html').read_bytes())
        self.assertEqual(self.backend.TOKEN_FILE.stat().st_mode & 0o777, 0o600)

    def test_task_validation_and_origin_protection(self):
        headers = self.authenticated_headers()
        headers.update({'Content-Type': 'application/json',
                        'Origin': 'http://127.0.0.1:' + str(self.server.server_port)})
        task = {'website': {'enabled': False, 'url': '', 'interval_seconds': 300},
                'photo': {'enabled': False, 'interval_seconds': 3600}}
        body = json.dumps(task)
        status, _, _ = self.request('POST', '/api/tasks', body, {'Content-Type': 'application/json'})
        self.assertEqual(status, 401)
        status, _, _ = self.request('POST', '/api/tasks', body, {**headers, 'Origin': 'http://example.com'})
        self.assertEqual(status, 403)
        status, _, data = self.request('POST', '/api/tasks', body, headers)
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(data)['website']['enabled'])
        saved = json.loads(self.backend.SETTINGS_FILE.read_text())
        task['website'].update(enabled=True, url='file:///etc/passwd')
        status, _, _ = self.request('POST', '/api/tasks', json.dumps(task), headers)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(self.backend.SETTINGS_FILE.read_text()), saved)

    def test_photo_path_traversal_rejected(self):
        status, _, _ = self.request('GET', '/photo/%2e%2e%2faccess-token', headers=self.authenticated_headers())
        self.assertEqual(status, 404)


if __name__ == '__main__':
    unittest.main()
