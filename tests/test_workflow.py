"""Isolated prototype integration checks. Never write fixtures to the application runtime."""
import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz
from fastapi.testclient import TestClient

import backend.app as module


def pdf_resume(scanned=False):
    text = ('Prototype Candidate\nprototype@example.test\nB.Tech Computer Science\nCGPA: 8.4\nBacklogs: 0\n'
            'Skills\nPython, SQL, Git, Pandas\nProjects\nSales Data Analysis\nInternships\nPython Developer Intern\n'
            'Certifications\nPython Certification\nAchievements\nCoding Competition Winner')
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((60, 60), text, fontsize=14)
    if scanned:
        image = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes('png')
        doc.close()
        doc = fitz.open()
        page = doc.new_page()
        page.insert_image(page.rect, stream=image)
    output = doc.tobytes()
    doc.close()
    return output


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='sprout-tests-')
        module.RUNTIME = Path(cls.temp.name)
        module.UPLOADS = module.RUNTIME / 'uploads'
        module.STATE_FILE = module.RUNTIME / 'state.json'
        module.state = {'jobs': {}, 'screenings': {}, 'reviews': {}}
        cls.context = TestClient(module.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        cls.temp.cleanup()

    def upload(self, scanned=False):
        r = self.client.post('/api/screenings?job_id=JOB_001', files={'file': ('resume.pdf', pdf_resume(scanned), 'application/pdf')})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()['id']

    def test_01_dataset_and_saved_model_ready(self):
        r = self.client.get('/api/health').json()
        self.assertEqual(r['rows'], 16508)
        self.assertTrue(r['model_ready'], r.get('model_error'))
        self.assertEqual(r['dataset'], 'AI_Fresher_Recruitment_ML_Dataset.csv')
        self.assertEqual(len(self.client.get('/api/jobs').json()), 4)

    def test_02_engineered_feature_parity(self):
        for raw in module.dataset.sample(30, random_state=42).to_dict('records'):
            derived = module.make_features(raw)
            for key in ['CGPA_Score','CGPA_Eligible','CGPA_Gap','Degree_Match','Skill_Match','Project_Count','Internship_Count',
                        'Certification_Count','Achievement_Count','Backlog_Score','Project_Score','Internship_Score','Certification_Score','Achievement_Score']:
                self.assertAlmostEqual(float(derived[key]), float(raw[key]), places=8, msg=key)

    def test_03_filter_export_and_model_segments(self):
        r = self.client.get('/api/candidates?job_id=JOB_001&q=Python&limit=3').json()
        self.assertGreater(r['total'], 0)
        self.assertEqual(len(r['items']), 3)
        self.assertTrue(all(x['job_id'] == 'JOB_001' for x in r['items']))
        app_id = r['items'][0]['id']
        prediction = self.client.post(f'/api/candidates/{app_id}/predict')
        self.assertEqual(prediction.status_code, 200, prediction.text)
        self.assertIn(prediction.json()['segment'], ['Potential Match','Lower Model Match'])
        bulk = self.client.post('/api/segments/run?job_id=JOB_002')
        self.assertEqual(bulk.status_code, 200, bulk.text)
        self.assertGreater(bulk.json()['processed'], 0)
        exported = self.client.get('/api/export?job_id=JOB_001')
        self.assertEqual(exported.status_code, 200)
        self.assertIn('Model Score', exported.text)

    def test_04_upload_confirm_predict_review_and_invalidate(self):
        screening_id = self.upload()
        extracted = self.client.get('/api/screenings/'+screening_id).json()
        self.assertEqual(extracted['status'], 'ready', extracted)
        self.assertEqual(extracted['data']['CGPA'], 8.4)
        self.assertIsNone(extracted['data']['Class 10 Percentage'])
        self.assertEqual(self.client.post(f'/api/candidates/{screening_id}/predict').status_code, 409)
        data = extracted['data']
        missing = self.client.put(f'/api/screenings/{screening_id}/data', json={'data': data})
        self.assertEqual(missing.status_code, 422)
        data.update({'Class 10 Percentage': 85, 'Class 12 Percentage': 88, 'Projects':['Sales Data Analysis'],
                     'Internships':[], 'Certifications':[], 'Achievements':[]})
        confirmed = self.client.put(f'/api/screenings/{screening_id}/data', json={'data': data})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        mapped = self.client.get(f'/api/screenings/{screening_id}/mapped-data').json()
        self.assertEqual(len(mapped['raw_record']), 23)
        self.assertEqual(mapped['feature_count'], 34)
        self.assertEqual(mapped['raw_record']['Number of Internships'], 0)
        predicted = self.client.post(f'/api/candidates/{screening_id}/predict')
        self.assertEqual(predicted.status_code, 200, predicted.text)
        self.assertTrue(0 <= predicted.json()['probability'] <= 1)
        reviewed = self.client.patch(f'/api/candidates/{screening_id}/review', json={'status':'Shortlisted'})
        self.assertEqual(reviewed.status_code, 200)
        data['CGPA'] = 8.6
        self.client.put(f'/api/screenings/{screening_id}/data', json={'data':data})
        edited = self.client.get('/api/screenings/'+screening_id).json()
        self.assertIsNone(edited['probability'])
        self.assertEqual(edited['segment'], 'Needs Data Review')
        self.assertEqual(edited['review'], 'Shortlisted')
        self.assertEqual(self.client.get(f'/api/screenings/{screening_id}/resume').status_code, 200)

    def test_05_scanned_pdf_real_ocr(self):
        screening_id = self.upload(scanned=True)
        r = self.client.get('/api/screenings/'+screening_id).json()
        self.assertEqual(r['status'], 'ready', r.get('error'))
        self.assertIn('Page 1: OCR', r['extraction_methods'])
        self.assertIn('Python', r['text'])
        self.assertIsNone(r['data']['Class 10 Percentage'])

    def test_06_invalid_uploads_and_ranges(self):
        parsed = module.parse_resume('Prototype Candidate\nGPA: 3.8/4\nClass 10 Percentage: 85%\nClass XII: 88.5%')
        self.assertIsNone(parsed['CGPA'])
        self.assertEqual(parsed['Class 10 Percentage'], 85)
        self.assertEqual(parsed['Class 12 Percentage'], 88.5)
        r = self.client.post('/api/screenings?job_id=JOB_001', files={'file':('bad.pdf', b'not a PDF', 'application/pdf')})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.client.get('/api/screenings/not-a-real-id/resume').status_code, 404)
        self.assertEqual(self.client.post('/api/candidates/missing/predict').status_code, 404)
        self.assertTrue(module.validate_confirmed({'CGPA':99, 'Backlogs':-1}))

    def test_07_job_creation_edit_and_restart_persistence(self):
        payload = {'title':'Prototype Test Position','required_skills':['Python','SQL'], 'preferred_degree':['B.Tech'],
                   'minimum_cgpa':7, 'openings':2,'status':'Active'}
        created = self.client.post('/api/jobs', json=payload)
        self.assertEqual(created.status_code, 200)
        job_id = created.json()['id']
        payload['status'] = 'Closed'
        self.assertEqual(self.client.put('/api/jobs/'+job_id,json=payload).status_code, 200)
        self.assertEqual(self.client.post('/api/screenings?job_id='+job_id,files={'file':('resume.pdf',pdf_resume(),'application/pdf')}).status_code, 422)
        self.assertTrue(module.STATE_FILE.exists())
        module.initialize()
        self.assertEqual(module.find_job(job_id)['status'], 'Closed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
