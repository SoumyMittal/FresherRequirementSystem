import unittest

from backend.resume_validation import specialization_facts


class SpecializationTests(unittest.TestCase):
    def test_combined_names_are_extracted_whole(self):
        for name in ('Artificial Intelligence and Data Science', 'Artificial Intelligence & Data Science',
                     'AI and Data Science', 'AI & DS', 'Computer Science and Engineering',
                     'Electronics and Communication Engineering', 'Electrical and Electronics Engineering',
                     'Mathematics and Computing', 'Information Technology and Management',
                     'Operations Research and Industrial Analytics'):
            with self.subTest(name=name):
                clause = f'B.Tech. in {name}  Expected Graduation: 2029'
                self.assertEqual(list(specialization_facts([clause]).values()),
                                 [(name, [{'page': 1, 'text': clause}])])

    def test_wrapped_name_and_equivalent_mentions_keep_both_sources(self):
        pages = ['B.Tech in Artificial Intelligence and\nData Science. Interested in Python.',
                 'Specialization: AI & DS']
        self.assertEqual(list(specialization_facts(pages).values()), [
            ('Artificial Intelligence and Data Science', [
                {'page': 1, 'text': pages[0]},
                {'page': 2, 'text': pages[1]},
            ])
        ])

    def test_distinct_education_values_remain_distinct(self):
        for source in ('Specializations: Artificial Intelligence; Data Science',
                       'Specializations: Artificial Intelligence, Data Science',
                       'B.Tech in Artificial Intelligence\nM.Sc in Data Science'):
            with self.subTest(source=source):
                self.assertEqual(list(specialization_facts([source])),
                                 ['artificial intelligence', 'data science'])

    def test_skills_and_project_mentions_do_not_fill_unknown_specialization(self):
        source = ('B.Tech student. Interested in Artificial Intelligence and Data Science.\n'
                  'Skills: Artificial Intelligence & Data Science\nProjects: Data Science\nB.Tech in progress')
        self.assertEqual(specialization_facts([source]), {})
