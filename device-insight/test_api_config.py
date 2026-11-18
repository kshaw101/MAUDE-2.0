import unittest
from types import SimpleNamespace
from api_config import normalize_key, resolve_api_key, key_problem, public_api_error


class ApiConfigurationTests(unittest.TestCase):
    def test_copied_assignment_and_quotes(self):
        self.assertEqual(normalize_key(' OPENAI_API_KEY="sk-example-fake" \n'), 'sk-example-fake')
        self.assertEqual(normalize_key('Bearer sk-example-fake'), 'sk-example-fake')

    def test_pasted_key_overrides_environment(self):
        self.assertEqual(resolve_api_key('sk-new-fake', 'sk-old-fake'), 'sk-new-fake')
        self.assertEqual(resolve_api_key('', 'sk-old-fake'), 'sk-old-fake')

    def test_masked_and_malformed_input_detected_without_echo(self):
        for value in ['sk-fake...123', 'sk-fake***123', 'sk-fake\n123', 'my-key-name']:
            message = key_problem(value)
            self.assertTrue(message)
            self.assertNotIn(value, message)

    def test_error_never_echoes_secret_fragments(self):
        error = SimpleNamespace(status_code=401, message='secret-do-not-print', body={})
        message = public_api_error(error)
        self.assertIn('401', message)
        self.assertIn('No restart', message)
        self.assertNotIn('secret-do-not-print', message)

    def test_quota_and_access_errors_are_separate(self):
        quota = SimpleNamespace(status_code=429, body={'code': 'insufficient_quota'})
        self.assertIn('insufficient quota', public_api_error(quota))
        self.assertIn('model', public_api_error(SimpleNamespace(status_code=403)))


if __name__ == '__main__':
    unittest.main()
