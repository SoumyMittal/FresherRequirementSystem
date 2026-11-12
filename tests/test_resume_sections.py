import unittest
from backend.resume_sections import (
    extract_sections,
    extract_canonical_entries,
    reconcile_and_deduplicate,
    derive_counts,
    ResumeEntry
)


class SectionExtractionTests(unittest.TestCase):
    def test_titles_descriptions_and_experience_aliases(self):
        text = '''PROJECTS
Sales Dashboard | Python, SQL
• Built a dashboard with SQL queries.
• Implemented reusable chart components.
Loan Risk Predictor
Developed a classification pipeline.
EXPERIENCE
Python Developer Intern | Example Labs
June 2025 - August 2025
Worked on REST endpoints.
Software Engineer | Example Company
Developed internal tools.
ACHIEVEMENTS
• Won a college hackathon.
• Department Rank Holder
CERTIFICATIONS
Python Certification
EDUCATION
B.Tech Computer Science
'''
        values, evidence = extract_sections(text)
        self.assertEqual(values['Projects'], ['Sales Dashboard', 'Loan Risk Predictor'])
        self.assertEqual(values['Internships'], ['Python Developer Intern'])
        self.assertEqual(len(values['Work Experience']), 2)
        self.assertEqual(len(values['Achievements']), 2)
        self.assertIn('Implemented', evidence['Projects'][0]['description'])
        self.assertEqual(values['Certifications'], ['Python Certification'])

    def test_missing_is_unknown_explicit_none_is_empty(self):
        values, _ = extract_sections('PROJECTS\nOne Project\nInternships\nNone\nSkills\nPython')
        self.assertEqual(values['Internships'], [])
        self.assertIsNone(values['Achievements'])

    def test_no_section_item_count_or_title_length_caps(self):
        titles = ['Project ' + str(i) + ' ' + ('A' * 160) for i in range(30)]
        values, _ = extract_sections('Projects\n' + '\n'.join(titles))
        self.assertEqual(len(values['Projects']), 30)

    def test_explicit_project_names_and_company_then_role(self):
        values, _ = extract_sections(
            'Projects\nProject Name: Sales Dashboard\nBuilt a SQL dashboard.\n'
            'Project Title: Inventory App\nImplemented stock alerts.\n'
            'Internships\nExample Labs\nRole: Python Developer Intern\nWorked on APIs.'
        )
        self.assertEqual(values['Projects'], ['Sales Dashboard', 'Inventory App'])
        self.assertEqual(values['Internships'], ['Python Developer Intern'])

    def test_duplicate_internship_regression_fixture(self):
        text = '''EXPERIENCE
AI/ML Intern                                      Jan 2026
Completed a project-based AI/ML internship focused on machine learning workflows and predictive analytics.
Marketing Intern                                  Jun 2026
Recognized for maintaining high standards of professionalism and commitment throughout the internship.
'''
        values, evidence = extract_sections(text)
        counts = derive_counts(values)

        self.assertEqual(counts['Number of Internships'], 2)
        self.assertEqual(values['Internships'], ['AI/ML Intern', 'Marketing Intern'])
        self.assertEqual(len(evidence['Internships']), 2)

        first_role = evidence['Internships'][0]
        second_role = evidence['Internships'][1]

        self.assertEqual(first_role['title'], 'AI/ML Intern')
        self.assertEqual(first_role['date_text'], 'Jan 2026')
        self.assertIn('Completed a project-based AI/ML internship', first_role['description'])

        self.assertEqual(second_role['title'], 'Marketing Intern')
        self.assertEqual(second_role['date_text'], 'Jun 2026')
        self.assertIn('Recognized for maintaining high standards', second_role['description'])

        # Neither description nor date becomes a standalone entry
        all_titles = [e['title'] for e in evidence['Internships']]
        self.assertNotIn('Completed a project-based', all_titles[0])
        self.assertNotIn('Jan 2026', all_titles)

    def test_project_grouping_bullets_and_tech_stack(self):
        text = '''PROJECTS
Farmer Crop Recommendation System | Python, Scikit-learn, Random Forest, Streamlit | GitHub
- Built a crop recommendation model using 2,200+ agricultural records, achieving 99% accuracy in evaluation.
- Implemented data preprocessing and modular OOP-based design; deployed an interactive Streamlit application for real-time recommendations.
Synthetic Employee Performance Dataset | Python, Pandas, HR Analytics | Kaggle
- Created and published a 5,000-record synthetic dataset with employee attributes and performance-related features.
'''
        values, evidence = extract_sections(text)
        counts = derive_counts(values)

        self.assertEqual(counts['Number of Projects'], 2)
        self.assertEqual(values['Projects'], ['Farmer Crop Recommendation System', 'Synthetic Employee Performance Dataset'])

        first_proj = evidence['Projects'][0]
        self.assertEqual(first_proj['title'], 'Farmer Crop Recommendation System')
        self.assertIn('Built a crop recommendation model', first_proj['description'])
        self.assertIn('Implemented data preprocessing', first_proj['description'])
        self.assertIn('Python', first_proj['technologies'])
        self.assertIn('Streamlit', first_proj['technologies'])
        self.assertIn('GitHub', first_proj['links'])

        second_proj = evidence['Projects'][1]
        self.assertEqual(second_proj['title'], 'Synthetic Employee Performance Dataset')
        self.assertIn('Created and published a 5,000-record', second_proj['description'])
        self.assertIn('Python', second_proj['technologies'])
        self.assertIn('Pandas', second_proj['technologies'])
        self.assertIn('Kaggle', second_proj['links'])

    def test_publication_routing_to_achievements(self):
        text = '''PROJECTS
Traffic Signal Optimization System | Python, SUMO
- Implemented a traffic simulation and control strategy.

PUBLICATIONS
An Interpretable Physics-Inspired Ensemble Learning Framework for Predicting Nanofluid Thermal Conductivity
- Research paper accepted and presented at an IEEE conference.
'''
        values, evidence = extract_sections(text)
        counts = derive_counts(values)

        self.assertEqual(counts['Number of Projects'], 1)
        self.assertEqual(counts['Number of Achievements'], 1)
        self.assertEqual(values['Projects'], ['Traffic Signal Optimization System'])
        self.assertEqual(
            values['Achievements'],
            ['An Interpretable Physics-Inspired Ensemble Learning Framework for Predicting Nanofluid Thermal Conductivity']
        )
        self.assertEqual(evidence['Achievements'][0]['subtype'], 'publication')
        self.assertIn('IEEE conference', evidence['Achievements'][0]['description'])

    def test_publication_heading_variants(self):
        variants = [
            'Research Publications',
            'Conference Papers',
            'Journal Publications',
            'Awards & Publications',
            'Research Papers'
        ]
        for heading in variants:
            with self.subTest(heading=heading):
                text = f'''PROJECTS
Smart Grid Load Forecaster | Python
- Built load forecasting model.

{heading}
Deep Learning for Medical Image Segmentation
- Paper accepted at CVPR workshop.
'''
                values, evidence = extract_sections(text)
                counts = derive_counts(values)
                self.assertEqual(counts['Number of Projects'], 1, f'{heading} inflated project count')
                self.assertEqual(counts['Number of Achievements'], 1, f'{heading} missed achievement')
                self.assertEqual(values['Projects'], ['Smart Grid Load Forecaster'])
                self.assertEqual(values['Achievements'], ['Deep Learning for Medical Image Segmentation'])
                self.assertEqual(evidence['Achievements'][0]['subtype'], 'publication')

    def test_experience_layout_variants(self):
        # Variant A: Company before role
        t1 = '''WORK EXPERIENCE
QSkill
AI/ML Intern | Jan 2026 – Feb 2026
- Built predictive analytics workflows.
- Evaluated model performance.
'''
        v1, e1 = extract_sections(t1)
        self.assertEqual(len(v1['Internships']), 1)
        self.assertEqual(e1['Internships'][0]['title'], 'AI/ML Intern')
        self.assertEqual(e1['Internships'][0]['organization'], 'QSkill')
        self.assertIn('Jan 2026', e1['Internships'][0]['date_text'])
        self.assertIn('Evaluated model performance', e1['Internships'][0]['description'])

        # Variant B: Role then company with mode then date
        t2 = '''PROFESSIONAL EXPERIENCE
AI/ML Intern
QSkill (Virtual)
Jan 2026 – Feb 2026
- Developed ML workflows.
'''
        v2, e2 = extract_sections(t2)
        self.assertEqual(len(v2['Internships']), 1)
        self.assertEqual(e2['Internships'][0]['title'], 'AI/ML Intern')
        self.assertEqual(e2['Internships'][0]['organization'], 'QSkill (Virtual)')
        self.assertIn('Jan 2026', e2['Internships'][0]['date_text'])

        # Variant C: Single dash line
        t3 = '''EXPERIENCE
AI/ML Intern — QSkill — Jan 2026
Completed a project-based internship.
Marketing Intern — Company B — Jun 2026
Maintained high standards of professionalism.
'''
        v3, e3 = extract_sections(t3)
        self.assertEqual(len(v3['Internships']), 2)
        self.assertEqual(e3['Internships'][0]['organization'], 'QSkill')
        self.assertEqual(e3['Internships'][1]['organization'], 'Company B')

    def test_same_title_internships_with_different_dates_remain_separate(self):
        text = '''EXPERIENCE
AI/ML Intern | Company A | Jan 2025 – Mar 2025
- Built data extraction pipelines.
AI/ML Intern | Company A | Jan 2026 – Mar 2026
- Deployed real-time inference model.
'''
        values, evidence = extract_sections(text)
        self.assertEqual(len(values['Internships']), 2)
        self.assertEqual(values['Internships'], ['AI/ML Intern', 'AI/ML Intern'])
        self.assertEqual(evidence['Internships'][0]['date_text'], 'Jan 2025 – Mar 2025')
        self.assertEqual(evidence['Internships'][1]['date_text'], 'Jan 2026 – Mar 2026')

    def test_details_never_become_standalone_entries(self):
        text = '''EXPERIENCE
June 2025 - August 2025
Example Company
https://example.com
Python | SQL | Machine Learning
Python Developer Intern
- Developed REST API endpoints.
99% accuracy achieved in model testing.
'''
        values, evidence = extract_sections(text)
        self.assertEqual(len(values['Internships']), 1)
        self.assertEqual(values['Internships'][0], 'Python Developer Intern')
        entry = evidence['Internships'][0]
        self.assertIn('June 2025', entry['date_text'])
        self.assertIn('accuracy', entry['description'])

    def test_normal_employment_not_misclassified_as_internship(self):
        text = '''EXPERIENCE
Senior Software Engineer | Tech Corp
Jan 2024 - Present
Led backend architecture migration.
Data Analyst Intern | Analytics LLC
Jun 2023 - Dec 2023
Built reporting dashboards.
'''
        values, evidence = extract_sections(text)
        self.assertEqual(values['Internships'], ['Data Analyst Intern'])
        self.assertEqual(len(values['Work Experience']), 2)

    def test_local_and_gemini_deduplication(self):
        local_entries = {
            'Projects': [
                ResumeEntry(
                    category='project',
                    title='Crop Recommendation System',
                    technologies=['Python', 'Scikit-learn'],
                    description='Built ML model for crop recommendation.',
                    source_text='Crop Recommendation System\nBuilt ML model.'
                )
            ],
            'Internships': [
                ResumeEntry(
                    category='internship',
                    title='AI/ML Intern',
                    organization='QSkill',
                    date_text='Jan 2026',
                    description='Focused on predictive workflows.'
                )
            ],
            'Work Experience': [],
            'Certifications': [],
            'Achievements': []
        }

        gemini_entries = {
            'Projects': [
                ResumeEntry(
                    category='project',
                    title='Crop Recommendation System',
                    technologies=['Streamlit', 'Random Forest'],
                    links=['GitHub'],
                    description='Deployed Streamlit interactive interface.',
                    source_text='Crop Recommendation System | GitHub'
                )
            ],
            'Internships': [
                ResumeEntry(
                    category='internship',
                    title='AI/ML Intern',
                    organization='QSkill',
                    date_text='Jan 2026',
                    description='Focused on predictive workflows.'
                )
            ],
            'Certifications': [],
            'Achievements': []
        }

        reconciled_values, reconciled_evidence = reconcile_and_deduplicate(local_entries, gemini_entries)
        # Deduplication check: projects and internships are not doubled
        self.assertEqual(len(reconciled_values['Projects']), 1)
        self.assertEqual(len(reconciled_values['Internships']), 1)

        proj = reconciled_evidence['Projects'][0]
        self.assertIn('Python', proj['technologies'])
        self.assertIn('Streamlit', proj['technologies'])
        self.assertIn('GitHub', proj['links'])
        self.assertIn('Built ML model', proj['description'])
        self.assertIn('Deployed Streamlit', proj['description'])


if __name__ == '__main__':
    unittest.main()
