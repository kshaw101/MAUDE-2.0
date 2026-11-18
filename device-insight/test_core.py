"""Run: python -m unittest -v test_core.py. No API key or API spending."""
import json
import unittest
import tempfile
from pathlib import Path
import zipfile
from types import SimpleNamespace

from core import (demo_reports, validate_reports, fit_model, search_reports,
                  run_agent, validate_answer)


class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df, cls.vec, cls.matrix, cls.km, cls.score = fit_model(demo_reports(), 5)

    def test_training_and_search(self):
        self.assertEqual(len(self.df), 36)
        self.assertEqual(self.df.cluster.nunique(), 5)
        self.assertIsNotNone(self.score)
        rows = search_reports(self.df, self.vec, self.matrix, 'battery')
        self.assertGreater(len(rows), 0)
        self.assertIn('battery', rows.iloc[0].narrative.lower())
        exact = search_reports(self.df, self.vec, self.matrix, 'DEMO-001')
        self.assertEqual(exact.iloc[0].report_id, 'DEMO-001')

    def test_unmatched_query_returns_no_evidence(self):
        self.assertTrue(search_reports(self.df, self.vec, self.matrix, 'zzzxxyyqqq').empty)

    def test_missing_and_duplicate_ids_rejected(self):
        bad = demo_reports().drop(columns='narrative')
        with self.assertRaises(ValueError):
            validate_reports(bad)
        bad = demo_reports()
        bad.loc[1, 'report_id'] = bad.loc[0, 'report_id']
        with self.assertRaises(ValueError):
            validate_reports(bad)

    def test_missing_cells_and_oversize_rejected(self):
        bad = demo_reports()
        bad.loc[0, 'narrative'] = ''
        with self.assertRaises(ValueError):
            validate_reports(bad)
        bad.loc[0, 'narrative'] = 'x' * 20001
        with self.assertRaises(ValueError):
            validate_reports(bad)

    def test_degenerate_training_rejected(self):
        bad = demo_reports()
        bad['narrative'] = 'same repeated words'
        with self.assertRaises(ValueError):
            fit_model(bad, 5)

    def test_theme_counts_stable_between_fits(self):
        other, *_ = fit_model(demo_reports(), 5)
        self.assertEqual(self.df.cluster.tolist(), other.cluster.tolist())

    def test_unknown_citation_rejected(self):
        answer = {'summary': 'Summary', 'observations': [
            {'text': 'Unsupported', 'report_ids': ['NOT-RETRIEVED']}], 'limitations': 'Demo'}
        with self.assertRaises(ValueError):
            validate_answer(answer, {'DEMO-001': {}})

    def test_bulk_reader_skips_overlong_rows_without_losing_next_record(self):
        from prepare_local_subset import records
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sample.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('sample.txt', 'MDR_REPORT_KEY|FOI_TEXT\n'
                           + '1|' + 'x' * 120000 + '\n2|intact narrative\n')
            self.assertEqual(list(records(path)), [{'MDR_REPORT_KEY': '2', 'FOI_TEXT': 'intact narrative'}])

    def test_agent_executes_tools_in_selected_scope(self):
        mask = self.df.device.eq('Demo Infusion Pump')
        scoped = self.df[mask].reset_index(drop=True)
        scoped_matrix = self.matrix[self.df.index[mask].to_numpy()]
        # A scripted API substitute tests dispatch and grounding, not live model behavior.
        call = SimpleNamespace(type='function_call', name='search_reports',
                               arguments=json.dumps({'query': 'battery'}), call_id='call_test')
        count_call = SimpleNamespace(type='function_call', name='get_theme_counts',
                                     arguments='{}', call_id='call_count')
        response1 = SimpleNamespace(output=[call])
        response2 = SimpleNamespace(output=[count_call])
        response3 = SimpleNamespace(output=[])
        response4 = SimpleNamespace(output_text=json.dumps({
            'summary': 'Fictional battery examples.',
            'observations': [{'text': 'Power loss was described.', 'report_ids': ['DEMO-001']}],
            'limitations': 'Fictional examples only.'}))
        replies = iter([response1, response2, response3, response4])
        requests = []

        def create(**kwargs):
            requests.append(kwargs.copy())
            return next(replies)

        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        result = run_agent(client, 'test-model', 'battery issues', scoped,
                           self.vec, scoped_matrix)
        self.assertEqual(len(result['trace']), 2)
        self.assertGreater(len(result['evidence']), 0)
        self.assertTrue(all(row['device'] == 'Demo Infusion Pump' for row in result['evidence']))
        self.assertTrue(all(request['store'] is False for request in requests))


if __name__ == '__main__':
    unittest.main()
