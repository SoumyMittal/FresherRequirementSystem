import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pandas as pd
import pymupdf as fitz
from fastapi.testclient import TestClient

import backend.app as app
from backend.pipeline.feature_engineering import make_features
from backend.pipeline.missing_values import prepare_model_record
from backend.pipeline.schema import NUMERIC_BOUNDS, RAW_COLUMNS
from test_gemini_parser import response_payload, wrapped

SAMPLES = app.ROOT / 'samples' / 'resumes'


def resume(name, lines, email=''):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), f'{name}\n{email}\nB.Tech Computer Science\nSkills: Python, SQL\n{lines}')
        return doc.tobytes()


class BatchScreeningTests(unittest.TestCase):
    def setUp(self):
        temp = self.enterContext(tempfile.TemporaryDirectory())
        runtime = Path(temp)
        self.enterContext(patch.multiple(app, RUNTIME=runtime, UPLOADS=runtime / 'uploads',
                                        STATE_FILE=runtime / 'state.json', state={key: {} for key in app.STATE_KEYS}))
        self.enterContext(patch.dict('os.environ', {'GEMINI_API_KEY': ''}))
        self.client = self.enterContext(TestClient(app.app))

    def upload(self, files, job='JOB_004', key=None):
        response = self.client.post('/api/batches', params={'job_id': job, 'upload_key': key or str(uuid4())},
                                    files=[('files', (name, data, 'application/pdf')) for name, data in files])
        self.assertEqual(response.status_code, 202, response.text)
        return self.batch(response.json()['id'])

    def batch(self, batch_id):
        return self.client.get('/api/batches/' + batch_id).json()

    def profile(self, item):
        return self.client.get('/api/screenings/' + item['application_id']).json()

    def run_batch(self, batch_id):
        response = self.client.post('/api/batches/' + batch_id + '/run')
        self.assertEqual(response.status_code, 202, response.text)
        return self.batch(batch_id)['run']

    def test_batch_inference_routing_defaults_and_audit(self):
        batch = self.upload([
            ('zero.pdf', resume('Zero Candidate', 'CGPA: 0\nBacklogs: 0\nProjects: None', 'zero@example.test')),
            ('missing.pdf', resume('Missing Candidate', 'Volunteered at a community center', 'missing@example.test')),
            ('invalid.pdf', resume('Invalid Candidate', 'CGPA: 11\nClass 10 Percentage: -4%\nBacklogs: -1')),
            ('corrupt.pdf', b'%PDF-1.7\ninvalid bytes'),
            ('wrong.pdf', b'not a PDF'),
        ])
        zero, missing, invalid = map(self.profile, batch['files'][:3])
        self.assertEqual(batch['counts'], dict(extracted=0, partial=3, failed=2, eligible=2, review=2, duplicates=0))
        self.assertEqual(zero['model_ready_record']['CGPA'], 0)
        self.assertEqual(missing['model_ready_record']['CGPA'], 0)
        self.assertEqual(missing['model_ready_record']['Projects'], 'Not Provided')
        self.assertEqual(missing['model_ready_record']['Number of Projects'], 0)
        self.assertEqual(zero['provenance']['CGPA']['status'], 'explicit_zero')
        self.assertEqual(zero['provenance']['Projects']['status'], 'explicit_empty')
        self.assertEqual(missing['provenance']['CGPA']['status'], 'absent')
        self.assertFalse(zero['job_checks']['cgpa_eligible'])
        self.assertIsNone(missing['job_checks']['cgpa_eligible'])
        self.assertIsNone(missing['raw_extracted']['CGPA'])
        self.assertEqual(invalid['raw_extracted']['CGPA'], 11)
        self.assertEqual(invalid['model_ready_record']['CGPA'], 11)
        self.assertIsNone(invalid['classifier_record'])
        self.assertEqual({i['field'] for i in invalid['field_issues']}, {'CGPA', 'Class 10 Percentage', 'Backlogs'})
        self.assertEqual(invalid['field_evidence']['CGPA'], [{'page': 1, 'text': 'CGPA: 11'}])
        with patch.object(app.artifact['pipeline'], 'predict_proba', return_value=np.array([[.01, .99], [.7, .3]])) as predict:
            run = self.run_batch(batch['id'])
            repeated = self.run_batch(batch['id'])
        self.assertEqual(run['id'], repeated['id'])
        self.assertEqual(predict.call_count, 1)
        frame = predict.call_args.args[0]
        self.assertEqual(list(frame.columns), app.artifact['feature_columns'])
        self.assertEqual(len(frame), 2)
        for row, profile in zip(frame.to_dict('records'), (zero, missing)):
            expected = make_features(profile['classifier_record'])
            self.assertEqual(row, {key: expected[key] for key in frame.columns})
        self.assertEqual(run['summary'], dict(assessed=2, shortlisted=1, non_shortlisted=1, failed=0, excluded=2))
        for route, expected in [('shortlist', zero), ('pool', missing)]:
            rows = self.client.get('/api/candidates', params={'route': route, 'job_id': 'JOB_004'}).json()['items']
            self.assertEqual([row['id'] for row in rows], [expected['id']])
        self.assertEqual(self.client.get('/api/candidates?route=review').json()['total'], 2)
        audit = app.state['model_runs'][run['id']]
        self.assertEqual(len(audit['model_hash']), 64)
        self.assertEqual(audit['job']['id'], 'JOB_004')
        self.assertEqual(audit['outcomes'][zero['id']]['Model_Rank'], 1)
        app.initialize()
        self.assertEqual(self.batch(batch['id'])['run']['id'], run['id'])
        self.assertFalse(self.batch(batch['id'])['can_run'])

    def test_duplicate_detection_is_job_scoped_and_upload_retry_is_idempotent(self):
        pdf = resume('Same Candidate', 'CGPA: 8', 'candidate@example.test')
        revised = resume('Same Candidate', 'CGPA: 9', 'CANDIDATE@example.test')
        key = str(uuid4())
        files = [('first.pdf', pdf), ('copy.pdf', pdf), ('revised.pdf', revised)]
        batch = self.upload(files, key=key)
        self.assertEqual(batch['id'], self.upload(files, key=key)['id'])
        first, copy, second = batch['files']
        self.assertEqual(first['application_id'], copy['application_id'])
        self.assertTrue(copy['duplicate'])
        self.assertEqual(batch['counts']['duplicates'], 3)
        self.assertEqual(self.profile(first)['possible_duplicates'][0]['application_id'], second['application_id'])
        separate = self.upload([('same.pdf', pdf)], job='JOB_001')
        separate_profile = self.profile(separate['files'][0])
        self.assertNotEqual(separate_profile['id'], first['application_id'])
        self.assertEqual(separate_profile['classifier_record']['Job ID'], 'JOB_001')
        self.assertEqual(len(app.state['screenings']), 3)

    def test_retry_runs_only_failed_extraction_and_real_ocr_is_per_page(self):
        scanned = SAMPLES / '02_ml_engineer_scanned.pdf'
        mixed = SAMPLES / '05_software_engineer_mixed.pdf'
        text = SAMPLES / '01_python_developer_text.pdf'
        original = app.extract_resume

        def interrupt(application_id):
            if app.state['screenings'][application_id]['filename'] == 'retry.pdf':
                app.update_screening(application_id, status='failed', error='Interrupted', route='review')
            else:
                original(application_id)

        with patch.object(app, 'extract_resume', side_effect=interrupt):
            batch = self.upload([(scanned.name, scanned.read_bytes()), (mixed.name, mixed.read_bytes()), ('retry.pdf', text.read_bytes())])
        scanned_item, mixed_item, failed = batch['files']
        self.assertIn('Page 1: OCR', self.profile(scanned_item)['extraction_methods'])
        profile = self.profile(mixed_item)
        self.assertTrue(any('embedded text' in method for method in profile['extraction_methods']))
        self.assertTrue(any('OCR' in method for method in profile['extraction_methods']))
        self.assertTrue(all(entry['page_numbers'] for entry in profile['evidence']['Projects']))
        path = f'/api/batches/{batch["id"]}/files/{failed["application_id"]}/retry'
        with patch.object(app, 'extract_resume', wraps=original) as extract:
            self.assertEqual(self.client.post(path).status_code, 202)
            self.assertEqual(self.client.post(path).status_code, 202)
        extract.assert_called_once_with(failed['application_id'])
        self.assertEqual(self.profile(failed)['attempts'], 2)
        self.assertEqual(self.profile(failed)['status'], 'ready')
        self.assertEqual(self.client.get('/api/screenings/' + failed['application_id'] + '/resume').content, text.read_bytes())

    def test_correction_job_changes_and_decisions_survive_reruns(self):
        batch = self.upload([('good.pdf', resume('Good Candidate', 'CGPA: 8')),
                             ('conflict.pdf', resume('Conflict Candidate', 'CGPA: 7\nCGPA: 9'))])
        good, conflict = map(self.profile, batch['files'])
        self.assertEqual(conflict['provenance']['CGPA']['status'], 'ambiguous')
        first = self.run_batch(batch['id'])
        self.assertEqual(first['summary']['assessed'], 1)
        base = '/api/candidates/' + good['id']
        self.assertEqual(self.client.patch(base + '/review', json={'status': 'Selected', 'reason': 'Interview complete'}).status_code, 200)
        corrected = self.client.put('/api/screenings/' + conflict['id'] + '/data', json={'data': {'CGPA': 9}}).json()
        self.assertTrue(corrected['model_ready'])
        self.assertEqual(corrected['raw_extracted']['CGPA'], 7)
        self.assertEqual(corrected['correction_history'][0]['changes']['CGPA']['value'], 9)
        second = self.run_batch(batch['id'])
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(second['summary']['assessed'], 2)
        job = app.find_job('JOB_004')
        job['minimum_cgpa'] = 9.5
        self.assertEqual(self.client.put('/api/jobs/JOB_004', json=job).status_code, 200)
        self.assertIsNone(self.client.get(base).json()['probability'])
        self.assertTrue(self.batch(batch['id'])['can_run'])
        self.run_batch(batch['id'])
        reviewed = self.client.get(base).json()
        self.assertEqual(reviewed['review'], 'Selected')
        self.assertEqual(reviewed['decision_history'][0]['reason'], 'Interview complete')
        self.assertFalse(reviewed['job_checks']['cgpa_eligible'])
        self.assertEqual(len(self.client.get('/api/batches/' + batch['id'] + '/runs').json()), 3)

    def test_model_failure_isolated_from_valid_records(self):
        batch = self.upload([('good.pdf', resume('Good Candidate', 'CGPA: 8')),
                             ('failure.pdf', resume('Failure Candidate', 'CGPA: 6'))])
        original = app.artifact['pipeline'].predict_proba

        def fail_one(frame):
            if 6 in frame['CGPA'].values:
                raise ValueError('test failure')
            return original(frame)

        with patch.object(app.artifact['pipeline'], 'predict_proba', side_effect=fail_one):
            run = self.run_batch(batch['id'])
        self.assertEqual(run['status'], 'partial')
        self.assertEqual(run['summary']['assessed'], 1)
        self.assertEqual(run['summary']['failed'], 1)
        failed = self.profile(batch['files'][1])
        self.assertEqual(failed['route'], 'not_assessed')
        self.assertIn(failed['id'], run['errors'])
        self.assertEqual(self.run_batch(batch['id'])['summary']['assessed'], 2)

    def test_job_capacity_validation_defaults_and_persistence(self):
        base = {'title': 'Capacity test', 'required_skills': ['Python'], 'preferred_degree': ['B.Tech'],
                'minimum_cgpa': 6, 'openings': 1}
        self.assertNotIn('JOB_004', app.state['jobs'])
        self.assertEqual(self.client.get('/api/jobs/JOB_004').json()['shortlisting_ratio'], 3.5)
        self.assertNotIn('JOB_004', app.state['jobs'])
        for openings, ratio, capacity in [(1, 3.5, 4), (2, 3.5, 7), (5, 3.5, 18), (10, 2, 20), (100, '0.07', 7)]:
            job = self.client.post('/api/jobs', json={**base, 'openings': openings, 'shortlisting_ratio': ratio,
                                                     'shortlist_capacity': 999}).json()
            self.assertEqual(job['shortlist_capacity'], capacity)
        job = self.client.post('/api/jobs', json=base).json()
        self.assertEqual(job['shortlist_capacity'], 4)
        path = '/api/jobs/' + job['id']
        for field, invalid in [('shortlisting_ratio', [0, -1, 'NaN', 'Infinity', '-Infinity', '', 'bogus', None, True, '0.0001']),
                               ('openings', [0, -1, 1.5, 'bad', None, True])]:
            for value in invalid:
                self.assertEqual(self.client.put(path, json={**base, field: value}).status_code, 422, str(value))
        self.assertEqual(self.client.put(path, json={**base, 'shortlisting_ratio': '2.125'}).status_code, 200)
        app.initialize()
        self.assertEqual(self.client.get(path).json()['shortlisting_ratio'], 2.125)
        self.assertEqual(self.client.put(path, json=base).json()['shortlisting_ratio'], 2.125)

    def test_legacy_batch_with_missing_application_remains_readable(self):
        batch = self.upload([('removed.pdf', resume('Removed Candidate', 'CGPA: 8'))])
        app.state['screenings'].pop(batch['files'][0]['application_id'])
        reloaded = self.batch(batch['id'])
        self.assertEqual(reloaded['counts']['failed'], 1)
        self.assertIsNone(reloaded['files'][0]['application_id'])
        self.assertFalse(reloaded['can_run'])

    def test_job_allocation_across_batches_with_explicit_configuration_activation(self):
        base = {'title': 'Capacity test', 'required_skills': ['Python'], 'preferred_degree': ['B.Tech'],
                'minimum_cgpa': 6, 'openings': 1, 'shortlisting_ratio': 2}
        job, other_job = [self.client.post('/api/jobs', json=base).json()['id'] for _ in range(2)]
        first = self.upload([('first.pdf', resume('First Candidate', 'CGPA: 8')),
                             ('below.pdf', resume('Below Candidate', 'CGPA: 7')),
                             ('invalid.pdf', resume('Invalid Candidate', 'CGPA: 11')),
                             ('corrupt.pdf', b'%PDF-1.7\ninvalid')], job=job)
        second = self.upload([('second.pdf', resume('Second Candidate', 'CGPA: 9')),
                              ('third.pdf', resume('Third Candidate', 'CGPA: 9'))], job=job)
        other = self.upload([('other.pdf', resume('Other Candidate', 'CGPA: 8'))], job=other_job)
        self.upload([('waiting.pdf', resume('Waiting Candidate', 'CGPA: 10'))], job=job)
        threshold = app.artifact['threshold']

        def model(frame):
            positive = np.array([threshold if cgpa >= 8 else threshold - .01 for cgpa in frame['CGPA']])
            return np.column_stack((1 - positive, positive))

        with patch.object(app.artifact['pipeline'], 'predict_proba', side_effect=model):
            first_run = self.run_batch(first['id'])
            self.assertEqual(first_run['summary'], dict(assessed=2, shortlisted=1, non_shortlisted=1, failed=0, excluded=2))
            self.run_batch(other['id'])
            second_run = self.run_batch(second['id'])
            first_id = first['files'][0]['application_id']
            winners = sorted(item['application_id'] for item in second['files'])
            self.assertEqual(second_run['allocation']['shortlisted_ids'], winners)
            self.assertEqual(second_run['allocation']['qualified'], 3)
            self.assertEqual(second_run['allocation']['assessed'], 4)
            self.assertEqual(self.profile(first['files'][0])['route'], 'pool')
            self.assertEqual(self.profile(second['files'][0])['pipeline_result']['Model_Rank'],
                             winners.index(second['files'][0]['application_id']) + 1)
            self.assertEqual(self.profile(other['files'][0])['route'], 'shortlist')
            self.client.patch(f'/api/candidates/{winners[1]}/review', json={'status': 'Selected'}).raise_for_status()

            self.client.put(f'/api/jobs/{job}', json={**base, 'shortlisting_ratio': 1}).raise_for_status()
            edited = self.client.get(f'/api/jobs/{job}').json()
            self.assertEqual(edited['shortlist_capacity'], 1)
            self.assertTrue(edited['allocation']['configuration_pending'])
            self.assertEqual(edited['allocation']['shortlisted'], 2)
            self.assertEqual(edited['allocation']['active']['run_id'], second_run['id'])
            history = edited['configuration_history'][0]
            self.assertEqual((history['previous']['shortlist_capacity'], history['current']['shortlist_capacity']), (2, 1))
            self.assertEqual(history['active_run_id'], second_run['id'])
            new_run = self.run_batch(first['id'])
            self.assertEqual(new_run['allocation']['shortlisted_ids'], winners[:1])
            self.assertEqual(new_run['summary']['shortlisted'], 0)
            self.assertEqual(self.run_batch(first['id'])['id'], new_run['id'])
            self.assertEqual(self.client.get(f'/api/candidates/{winners[1]}').json()['review'], 'Selected')
            self.assertEqual(app.state['model_runs'][first_run['id']]['allocation']['shortlisted_ids'], [first_id])
            self.assertEqual(app.state['model_runs'][second_run['id']]['job']['shortlisting_ratio'], 2)
            self.client.put(f'/api/jobs/{job}', json={**base, 'openings': 2, 'shortlisting_ratio': 1}).raise_for_status()
            refreshed = self.run_batch(first['id'])
            self.assertEqual(refreshed['allocation']['shortlisted_ids'], winners)
            self.assertEqual(self.profile(second['files'][0])['pipeline_result']['Number of Openings'], 2)

    def test_default_policy_compatibility_regression(self):
        frame = app.dataset
        model = app.artifact['pipeline']
        columns = app.artifact['feature_columns']
        pre = model.named_steps['preprocessor']
        self.assertEqual(list(model.feature_names_in_), columns)
        self.assertEqual(pre.named_transformers_['categorical'].named_steps['encoder'].handle_unknown, 'ignore')
        scaler = pre.named_transformers_['numeric'].named_steps['scaler']
        self.assertAlmostEqual(-scaler.mean_[0] / scaler.scale_[0], -9.1616882, places=5)
        reference_scores = model.predict_proba(frame[columns])[:, 1]
        high_scores = frame.assign(classifier_score=reference_scores).sort_values('classifier_score', ascending=False)
        indices = list(dict.fromkeys([*frame.iloc[::250].head(60).index, *high_scores.head(40).index]))
        masks = [('CGPA', 'Class 10 Percentage', 'Class 12 Percentage'), ('Backlogs', 'Specialization', 'Skills'),
                 tuple(field for field in RAW_COLUMNS if field in ('Projects', 'Internships', 'Certifications', 'Achievements')
                       or field.startswith('Number of ') and field != 'Number of Openings')]
        legacy, adapted, requested = [], [], []
        reference = frame.to_dict('records')
        for index, row in enumerate(frame.loc[indices, list(RAW_COLUMNS)].to_dict('records')):
            for field in masks[index % len(masks)]:
                row[field] = None
            legacy.append(prepare_model_record(row, reference)[0])
            adapted.append(app.prepared_model_record_for_raw(row)[0])
            requested.append({field: value if value is not None else 0 if field in NUMERIC_BOUNDS else 'Not Provided'
                              for field, value in row.items()})
        self.assertEqual(legacy, adapted)
        vectors = [[make_features(row) for row in records] for records in (legacy, adapted, requested)]
        historic, compatible, direct = [model.predict_proba(pd.DataFrame(rows)[columns])[:, 1] for rows in vectors]
        np.testing.assert_array_equal(historic, compatible)
        self.assertAlmostEqual(float(np.abs(historic - direct).max()), 0.9999761, places=5)
        threshold = app.artifact['threshold']
        self.assertEqual(np.count_nonzero((historic >= threshold) != (direct >= threshold)), 13)

    def test_unreliable_extraction_and_nonblocking_profile_warning(self):
        batch = self.upload([
            ('other-scale.pdf', resume('Scale Candidate', 'GPA: 3.8/4\nProjects')),
            ('contact.pdf', resume('Contact Candidate', 'CGPA: 8\nTechnical Skills: Elixir', 'malformed@address')),
            ('absent.pdf', resume('Absent Candidate', 'Candidate seeking entry-level role')),
        ])
        scale, contact, absent = map(self.profile, batch['files'])
        self.assertEqual(scale['route'], 'review')
        self.assertEqual(scale['provenance']['CGPA']['status'], 'ambiguous')
        self.assertEqual(scale['provenance']['Projects']['status'], 'unextractable')
        self.assertIsNone(scale['model_ready_record']['Number of Projects'])
        self.assertTrue(contact['model_ready'])
        self.assertFalse(next(item for item in contact['field_issues'] if item['field'] == 'Email')['blocking'])
        self.assertIn('Elixir', contact['raw_extracted']['Skills'])
        self.assertTrue(absent['model_ready'])
        self.assertEqual(absent['provenance']['Projects']['status'], 'absent')

    def test_diksham_sentence_reaches_batch_model_with_source_evidence(self):
        sentence = ('Motivated B.Tech student specializing in Artificial Intelligence and Data Science. '
                    'Passionate about leveraging Python and BI tools.')
        with fitz.open() as doc:
            page = doc.new_page(width=1000)
            page.insert_text((50, 50), 'Synthetic Candidate\n' + sentence +
                             '\nEducation\nB.Tech in AI & DS\nSkills: Python, SQL')
            pdf = doc.tobytes()
        for remote in (None, 'Artificial Intelligence and Data Science', 'AI & DS', 'Artificial Intelligence'):
            with self.subTest(remote=remote):
                payload = response_payload()
                payload['candidate']['cgpa'] = {'value': None, 'source_text': None}
                payload['candidate']['specialization'] = {'value': remote, 'source_text': sentence if remote else None}
                with patch.dict('os.environ', {'GEMINI_API_KEY': 'test-key' if remote else ''}), \
                     patch('urllib.request.urlopen', return_value=wrapped(payload)):
                    job = self.client.post('/api/jobs', json={
                        'title': 'Specialization regression', 'required_skills': ['Python'],
                        'preferred_degree': ['B.Tech'], 'minimum_cgpa': 7, 'openings': 1,
                    }).json()['id']
                    batch = self.upload([('Resume_v8.pdf', pdf)], job=job)
                item = batch['files'][0]
                profile = self.profile(item)
                self.assertEqual(batch['counts']['eligible'], 1)
                self.assertEqual(batch['counts']['review'], 0)
                for record in ('data', 'raw_extracted', 'model_ready_record', 'classifier_record'):
                    self.assertEqual(profile[record]['Specialization'], 'Artificial Intelligence and Data Science')
                self.assertIn({'page': 1, 'text': sentence}, profile['field_evidence']['Specialization'])
                self.assertFalse(any(finding['field'] == 'Specialization' for finding in profile['field_issues']))
                if remote:
                    self.assertEqual(profile['gemini_extracted']['Specialization'], 'Artificial Intelligence and Data Science')
                self.assertEqual(self.run_batch(batch['id'])['summary']['assessed'], 1)
                duplicate = self.upload([('Resume_v8.pdf', pdf)], job=job)['files'][0]
                self.assertTrue(duplicate['duplicate'])
                self.assertEqual(duplicate['application_id'], item['application_id'])

    def test_distinct_specializations_and_unrelated_validation_still_require_review(self):
        files = [
            ('separate.pdf', resume('Separate Candidate', 'Specializations: Artificial Intelligence; Data Science')),
            ('degrees.pdf', resume('Two Qualifications', 'M.Sc in Mathematics and Computing')),
            ('invalid.pdf', resume('Invalid Candidate', 'Major: Computer Science\nCGPA: 12')),
        ]
        batch = self.upload(files)
        separate, degrees, invalid = map(self.profile, batch['files'])
        for profile in (separate, degrees):
            self.assertIn('Specialization', {item['field'] for item in profile['field_issues']})
            self.assertFalse(profile['model_ready'])
        self.assertEqual({item['field'] for item in invalid['field_issues']}, {'CGPA'})
