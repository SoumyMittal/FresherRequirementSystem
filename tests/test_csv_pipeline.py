import csv
import hashlib
import math
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from backend.pipeline import RecruitmentPipeline
from backend.pipeline.config import MAXIMA, PipelineConfig
from backend.pipeline.feature_engineering import make_features
from backend.pipeline.model_inference import infer, validate_artifact
from backend.pipeline.pipeline import ValidationError
from backend.pipeline.recruitment_scoring import recruitment_score
from backend.pipeline.schema import RAW_COLUMNS, DERIVED_COLUMNS
from backend.pipeline.csv_export import write_csv


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = RecruitmentPipeline()
        cls.reference = pd.read_csv(cls.pipeline.config.reference_path, keep_default_na=False)
        cls.rows = cls.reference.iloc[:5][list(RAW_COLUMNS)].to_dict('records')

    def test_feature_parity_and_prediction_parity_full_reference(self):
        records = self.reference.to_dict('records')
        output, errors = self.pipeline.process_records(records)
        self.assertEqual(errors, [])
        self.assertEqual(len(output), len(records))
        frame = pd.DataFrame(output)
        for key in DERIVED_COLUMNS:
            self.assertLess(float((frame[key] - self.reference[key]).abs().max()), 1e-8, key)
        expected = infer(records, self.pipeline.artifact)
        self.assertLess(max(abs(a-b) for a,b in zip(frame['Model_Score'], expected)), 1e-10)
        self.assertTrue(all(math.isfinite(p) and 0 <= p <= 1 for p in expected))

    def test_small_csv_input_unchanged_and_deterministic(self):
        with tempfile.TemporaryDirectory() as folder:
            source, first, second = [Path(folder)/name for name in ('input.csv','first.csv','second.csv')]
            write_csv(source, self.rows, RAW_COLUMNS)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            a = self.pipeline.process_csv(source, first)
            b = self.pipeline.process_csv(source, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(a['output_rows'], 5)
            self.assertEqual(b['invalid_rows'], 0)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)
            self.assertEqual(MAXIMA['Project_Count'], 5)

    def test_duplicate_ids_report_all_affected_rows(self):
        rows = [dict(self.rows[0]), dict(self.rows[0])]
        with self.assertRaises(ValidationError) as ctx:
            self.pipeline.process_records(rows)
        self.assertEqual(len(ctx.exception.errors), 2)

    def test_strict_and_report_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'input.csv', Path(folder)/'output.csv'
            rows = [dict(r) for r in self.rows]
            rows[1]['CGPA'] = 'not-a-number'
            rows[2]['Backlogs'] = -1
            write_csv(source, rows, RAW_COLUMNS)
            with self.assertRaises(ValidationError):
                self.pipeline.process_csv(source, output)
            self.assertFalse(output.exists())
            self.assertTrue((Path(folder)/'output_Validation_Errors.csv').exists())
            result = self.pipeline.process_csv(source, Path(folder)/'valid.csv', strict=False)
            self.assertEqual(result['invalid_rows'], 2)
            self.assertEqual(result['output_rows'], 3)

    def test_bad_headers_and_path_protection(self):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder)/'input.csv', Path(folder)/'output.csv'
            for header in [('Application ID',), (*RAW_COLUMNS, 'CGPA')]:
                source.write_text(','.join(header)+'\n', encoding='utf-8')
                with self.assertRaises(ValueError):
                    self.pipeline.process_csv(source, output)
            write_csv(source, self.rows, RAW_COLUMNS)
            with self.assertRaises(ValueError):
                self.pipeline.process_csv(source, source)

    def test_unknown_categories_and_empty_lists(self):
        row = dict(self.rows[0], Degree='New Degree', Specialization='New Specialization', Projects='None', **{'Number of Projects':0})
        result, errors = self.pipeline.process_records([row])
        self.assertEqual(errors, [])
        self.assertEqual(result[0]['Project_Count'], 0)
        self.assertEqual(result[0]['Degree_Match'], 0)

    def test_rank_is_per_job_and_output_keeps_all_rows(self):
        output, _ = self.pipeline.process_records(self.rows)
        for job in {r['Job ID'] for r in output}:
            group = [r for r in output if r['Job ID'] == job]
            self.assertEqual(sorted(r['Model_Rank'] for r in group), list(range(1, len(group)+1)))
        self.assertEqual([r['Application ID'] for r in output], [r['Application ID'] for r in self.rows])

    def test_unknown_stays_missing_and_recovery_is_opt_in(self):
        a, b = dict(self.rows[0]), dict(self.rows[0])
        b['Application ID'] = 'ANOTHER_APPLICATION'
        b['CGPA'] = None
        with self.assertRaises(ValidationError):
            self.pipeline.process_records([a, b])
        output, _ = self.pipeline.process_records([a,b], recover=True)
        self.assertEqual(output[0]['CGPA'], output[1]['CGPA'])
        self.assertIn('CGPA', output[1]['Processing_Warnings'])

    def test_score_penalties_explicit_and_no_noise(self):
        features = make_features(dict(self.rows[0], CGPA=5, Degree='Other'))
        plain = recruitment_score(features)
        self.assertEqual(plain, recruitment_score(features))
        self.assertAlmostEqual(recruitment_score(features, True), round(plain*.7*.8, 2))

    def test_artifact_contract_rejects_leakage(self):
        broken = dict(self.pipeline.artifact, feature_columns=[*self.pipeline.artifact['feature_columns'], 'Shortlisted'])
        with self.assertRaises(ValueError):
            validate_artifact(broken)

    def test_preserves_historical_score_as_input_backup(self):
        raw = self.reference.iloc[0].to_dict()
        output, _ = self.pipeline.process_records([raw])
        self.assertEqual(output[0]['Input_Recruitment_Score'], raw['Recruitment_Score'])
        self.assertEqual(output[0]['Recruitment_Score'], recruitment_score(output[0]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
