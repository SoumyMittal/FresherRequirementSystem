import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from backend.gemini_parser import extract_with_gemini, parser_status, GeminiError


def response_payload():
    fields = {name: {'value': None, 'source_text': None} for name in
              ['full_name','email','degree','specialization','cgpa','class_10_percentage','class_12_percentage','backlogs']}
    fields['full_name'] = {'value':'Sample Candidate','source_text':'Sample Candidate'}
    fields['cgpa'] = {'value':8.4,'source_text':'CGPA: 8.4/10'}
    result = {'candidate':fields, 'skills':[{'title':'Python','description':None,'source_text':'Skills: Python, SQL'}],
              'projects':None,'internships':None,'certifications':None,'achievements':None}
    return result


def wrapped(result):
    return io.BytesIO(json.dumps({'candidates':[{'finishReason':'STOP', 'content':{'parts':[{'text':json.dumps(result)}]}}]}).encode())


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'GEMINI_API_KEY':'unit-test-not-a-real-key','GEMINI_MODEL':'gemini-flash-latest'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_requested_rest_model_and_evidence(self):
        with patch('urllib.request.urlopen', return_value=wrapped(response_payload())) as call:
            result = extract_with_gemini('Sample Candidate\nCGPA: 8.4/10\nSkills: Python, SQL')
        request = call.call_args.args[0]
        self.assertEqual(request.full_url, 'https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent')
        self.assertEqual(request.get_header('X-goog-api-key'), 'unit-test-not-a-real-key')
        self.assertEqual(result['data']['CGPA'], 8.4)
        self.assertIsNone(result['data']['Class 10 Percentage'])
        self.assertIsNone(result['data']['Projects'])
        self.assertEqual(result['data']['Skills'], ['Python'])
        self.assertIn('CGPA', result['evidence'])
        self.assertNotIn('unit-test-not-a-real-key', json.dumps(parser_status()))

    def test_unsupported_values_are_not_accepted(self):
        response = response_payload()
        response['candidate']['cgpa']['value'] = 9.9
        response['projects'] = [{'title':'Invented Project','description':None,'source_text':'not in resume'}]
        with patch('urllib.request.urlopen', return_value=wrapped(response)):
            result = extract_with_gemini('Sample Candidate\nCGPA: 8.4/10\nSkills: Python, SQL')
        self.assertIsNone(result['data']['CGPA'])
        self.assertIsNone(result['data']['Projects'])
        self.assertTrue(result['warnings'])

    def test_http_error_and_invalid_json_are_sanitized(self):
        error = urllib.error.HTTPError('https://example.test', 429, 'key=secret-string', {}, None)
        with patch('urllib.request.urlopen', side_effect=error):
            with self.assertRaises(GeminiError) as context:
                extract_with_gemini('Sample resume')
        self.assertIn('429', str(context.exception))
        self.assertNotIn('secret-string', str(context.exception))
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'not json')):
            with self.assertRaises(GeminiError):
                extract_with_gemini('Sample resume')

    def test_missing_key_does_not_send_request(self):
        with patch.dict(os.environ, {'GEMINI_API_KEY':''}), patch('urllib.request.urlopen') as call:
            with self.assertRaises(GeminiError):
                extract_with_gemini('Sample resume')
            call.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
