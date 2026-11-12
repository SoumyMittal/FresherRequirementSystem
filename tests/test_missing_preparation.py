import unittest
from backend.pipeline.missing_values import prepare_model_record
from backend.pipeline.validation import validate_records


class MissingPreparationTests(unittest.TestCase):
    def test_reference_fallbacks_preserve_originals_and_known_values(self):
        source = {'CGPA': 9.1, 'Backlogs': None, 'Projects': None, 'Number of Projects': None}
        reference = [{'CGPA': 7, 'Backlogs': 0, 'Number of Projects': 2, 'Specialization': 'CS'},
                     {'CGPA': 8, 'Backlogs': 2, 'Number of Projects': 4, 'Specialization': 'CS'}]
        prepared, audit = prepare_model_record(source, reference)
        self.assertEqual(prepared['CGPA'], 9.1)
        self.assertEqual(prepared['Backlogs'], 1)
        self.assertEqual(prepared['Number of Projects'], 3)
        self.assertEqual(prepared['Projects'], 'Not Provided')
        self.assertEqual(prepared['Specialization'], 'CS')
        self.assertIsNone(source['Backlogs'])
        self.assertNotIn('CGPA', audit)

    def test_invalid_known_values_are_not_silently_replaced(self):
        prepared, audit = prepare_model_record({'CGPA': 99}, [{'CGPA': 8}])
        self.assertEqual(prepared['CGPA'], 99)
        self.assertNotIn('CGPA', audit)
        self.assertTrue(validate_records([prepared])[1])
