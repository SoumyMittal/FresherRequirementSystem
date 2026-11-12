"""Isolated prototype integration checks. Never write fixtures to the application runtime."""
import tempfile
import unittest
from unittest.mock import patch
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
        cls.env = patch.dict('os.environ', {'GEMINI_API_KEY': ''})
        cls.env.start()
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
        cls.env.stop()

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
        self.assertEqual(self.client.post(f'/api/candidates/{screening_id}/predict').status_code, 200)
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

    def test_08_sample_pack_extracts_without_seeding_application_storage(self):
        import json
        expected = json.loads((module.ROOT/'samples/expected_results.json').read_text(encoding='utf-8'))
        for item in expected:
            with self.subTest(filename=item['filename']):
                path = module.ROOT/'samples/resumes'/item['filename']
                response = self.client.post('/api/screenings?job_id='+item['raw_record']['Job ID'],
                                            files={'file':(path.name,path.read_bytes(),'application/pdf')})
                self.assertEqual(response.status_code, 200, response.text)
                screening_id = response.json()['id']
                extracted = self.client.get('/api/screenings/'+screening_id).json()
                self.assertEqual(extracted['status'], 'ready', extracted.get('error'))
                self.assertFalse(extracted['confirmed'])
                self.assertEqual(extracted['data']['CGPA'], item['raw_record']['CGPA'])
                if item['mode'] in ('scanned','mixed'):
                    self.assertTrue(any('OCR' in method for method in extracted['extraction_methods']))
                if item['mode'] == 'mixed':
                    self.assertTrue(any('embedded text' in method for method in extracted['extraction_methods']))
                self.assertEqual(self.client.post(f'/api/candidates/{screening_id}/predict').status_code, 200)

    def test_09_gemini_failure_falls_back_and_does_not_auto_confirm(self):
        with patch.object(module, 'parser_status', return_value={'gemini_configured':True}), \
             patch.object(module, 'extract_with_gemini', side_effect=module.GeminiError('Gemini returned HTTP 429.')):
            screening_id = self.upload()
        result = self.client.get('/api/screenings/'+screening_id).json()
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['parser'], 'local')
        self.assertFalse(result['confirmed'])
        self.assertTrue(any('429' in warning and 'Local parsing' in warning for warning in result['warnings']))

    def test_10_review_mapping_matches_the_actual_classifier_input(self):
        screening_id = self.upload()
        data = self.client.get('/api/screenings/'+screening_id).json()['data']
        data.update({'Class 10 Percentage':85, 'Class 12 Percentage':88, 'Projects':['Sales Data Analysis'],
                     'Internships':[], 'Certifications':[], 'Achievements':[]})
        preview = self.client.post(f'/api/screenings/{screening_id}/input-preview',json={'data':data})
        self.assertEqual(preview.status_code, 200, preview.text)
        mapping=preview.json()
        self.assertEqual(mapping['raw_record']['Number of Projects'],1)
        self.assertEqual(mapping['raw_record']['Job ID'],'JOB_001')
        self.assertEqual(mapping['model_inputs']['Job Role'],'AI/ML Engineer')
        self.assertNotIn('Full Name',mapping['model_inputs'])
        self.assertFalse(self.client.get('/api/screenings/'+screening_id).json()['confirmed'])
        self.assertEqual(self.client.post(f'/api/candidates/{screening_id}/predict').status_code,200)
        self.client.put(f'/api/screenings/{screening_id}/data',json={'data':data})
        classifier=module.artifact['pipeline']
        with patch.object(classifier,'predict_proba',wraps=classifier.predict_proba) as call:
            predicted=self.client.post(f'/api/candidates/{screening_id}/predict')
        self.assertEqual(predicted.status_code,200,predicted.text)
        actual=call.call_args.args[0]
        self.assertEqual(list(actual.columns),module.artifact['feature_columns'])
        self.assertEqual(actual.iloc[0].to_dict(),mapping['model_inputs'])
        changed=dict(data,CGPA=6.5)
        updated=self.client.post(f'/api/screenings/{screening_id}/input-preview',json={'data':changed}).json()
        self.assertEqual(updated['model_inputs']['CGPA_Score'],.65)
        self.assertEqual(self.client.get('/api/screenings/'+screening_id).json()['data']['CGPA'],8.4)

    def test_11_export_is_a_real_pipeline_input_and_drafts_preserve_unknowns(self):
        import csv
        import io
        from backend.pipeline.schema import RAW_COLUMNS
        first=self.upload()
        draft=self.client.post('/api/screenings/export-csv',json={'screening_ids':[first],'mode':'draft'})
        self.assertEqual(draft.status_code,200,draft.text)
        reader=csv.DictReader(io.StringIO(draft.content.decode('utf-8-sig')))
        self.assertEqual(reader.fieldnames,list(RAW_COLUMNS))
        row=next(reader)
        self.assertEqual(row['Class 10 Percentage'],'')
        self.assertEqual(self.client.post('/api/screenings/export-csv',json={'screening_ids':[first]}).status_code,200)
        data=self.client.get('/api/screenings/'+first).json()['data']
        data.update({'Class 10 Percentage':85,'Class 12 Percentage':88,'Projects':['Inventory, CSV Import'],
                     'Internships':[],'Certifications':[],'Achievements':[]})
        self.assertEqual(self.client.put(f'/api/screenings/{first}/data',json={'data':data}).status_code,200)
        exported=self.client.post('/api/screenings/export-csv',json={'screening_ids':[first]})
        self.assertEqual(exported.status_code,200,exported.text)
        source=module.RUNTIME/'exported-input.csv'
        source.write_bytes(exported.content)
        output=module.RUNTIME/'exported-scored.csv'
        result=module.recruitment_pipeline.process_csv(source,output)
        self.assertEqual(result['successful_predictions'],1)
        self.assertEqual(result['invalid_rows'],0)
        self.assertEqual(self.client.post('/api/screenings/export-csv',json={'screening_ids':[first,first]}).status_code,422)
        self.assertEqual(self.client.post('/api/screenings/export-csv',json={'screening_ids':['not-found']}).status_code,404)

    def test_12_tiny_classifier_outputs_preserve_separate_recruitment_score(self):
        import numpy as np
        screening_id=self.upload()
        data=self.client.get('/api/screenings/'+screening_id).json()['data']
        data.update({'Class 10 Percentage':85,'Class 12 Percentage':88,'Projects':['Sales Data Analysis'],
                     'Internships':[],'Certifications':[],'Achievements':[]})
        self.client.put(f'/api/screenings/{screening_id}/data',json={'data':data})
        probability=5.4713675199463515e-11
        with patch.object(module.artifact['pipeline'],'predict_proba',return_value=np.array([[1-probability,probability]])):
            result=self.client.post(f'/api/candidates/{screening_id}/predict').json()
        self.assertEqual(result['probability'],probability)
        self.assertGreater(result['recruitment_score'],0)
        stored=self.client.get('/api/screenings/'+screening_id).json()
        self.assertEqual(stored['probability'],probability)
        self.assertEqual(stored['recruitment_score'],result['recruitment_score'])
        listed=self.client.get('/api/candidates?q='+screening_id).json()['items'][0]
        self.assertEqual(listed['recruitment_score'],result['recruitment_score'])
        self.client.put(f'/api/screenings/{screening_id}/data',json={'data':dict(data,CGPA=7)})
        listed=self.client.get('/api/candidates?q='+screening_id).json()['items'][0]
        self.assertIsNone(listed['recruitment_score'])

    def test_13_missing_values_are_handled_before_export_and_prediction(self):
        screening_id=self.upload()
        data=self.client.get('/api/screenings/'+screening_id).json()['data']
        data.update({'Backlogs':'Not provided','Class 10 Percentage':None,'Class 12 Percentage':None,
                     'Internships':None,'Achievements':None})
        saved=self.client.put(f'/api/screenings/{screening_id}/data',json={'data':data,'allow_incomplete':True})
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertTrue(saved.json()['confirmed'])
        self.assertTrue(saved.json()['model_ready'])
        self.assertIsNone(saved.json()['data']['Backlogs'])
        self.assertFalse(saved.json()['validation_issues'])
        self.assertIn('Backlogs',saved.json()['imputed_fields'])
        self.assertEqual(self.client.post(f'/api/candidates/{screening_id}/predict').status_code,200)
        self.assertEqual(self.client.post('/api/screenings/export-csv',json={'screening_ids':[screening_id],'mode':'draft'}).status_code,200)
        self.assertEqual(self.client.post('/api/screenings/export-csv',json={'screening_ids':[screening_id]}).status_code,200)

    def test_14_more_than_fifteen_pages_can_be_extracted(self):
        doc=fitz.open()
        for number in range(17):
            page=doc.new_page()
            page.insert_text((50,60),'Example Candidate resume text with sufficient embedded text for page '+str(number))
        data=doc.tobytes();doc.close()
        result=self.client.post('/api/screenings?job_id=JOB_001',files={'file':('long-resume.pdf',data,'application/pdf')})
        self.assertEqual(result.status_code,200,result.text)
        item=self.client.get('/api/screenings/'+result.json()['id']).json()
        self.assertEqual(item['total_pages'],17)
        self.assertEqual(len(item['extraction_methods']),17)


if __name__ == '__main__':
    unittest.main(verbosity=2)
