"""Headless Streamlit interactions; requires installed requirements."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class InterfaceTests(unittest.TestCase):
    def test_pages_search_and_ml_controls(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': ''}):
            app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            app.sidebar.radio[1].set_value('Fictional demo').run(timeout=60)
            app.text_input[0].set_value('battery').run()
            self.assertEqual(len(app.exception), 0)
            self.assertGreater(len(app.expander), 0)
            app.text_input[0].set_value('zzzxxyyqqq').run()
            self.assertEqual(len(app.expander), 0)
            app.sidebar.radio[0].set_value('ML dashboard').run()
            self.assertEqual(len(app.exception), 0)
            app.sidebar.slider[0].set_value(3).run(timeout=60)
            self.assertEqual(len(app.exception), 0)
            app.sidebar.radio[0].set_value('AI research assistant').run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(app.button[0].disabled)
            app.sidebar.radio[0].set_value('About & demo').run()
            self.assertEqual(len(app.exception), 0)

    def test_api_key_can_override_a_bad_environment_key_without_restart(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-old-fake'}):
            app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=60)
            app.sidebar.radio[0].set_value('AI research assistant').run()
            self.assertEqual(len(app.exception), 0)
            self.assertEqual(app.text_input[0].label, 'OpenAI API key')
            app.text_input[0].set_value('OPENAI_API_KEY="sk-new-fake"').run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(any('overrides .env' in element.value for element in app.caption))
            self.assertFalse(app.button[0].disabled)
            app.text_input[0].set_value('sk-masked...key').run()
            self.assertTrue(app.button[0].disabled)
            self.assertTrue(any('masked' in element.value for element in app.error))


if __name__ == '__main__':
    unittest.main()
