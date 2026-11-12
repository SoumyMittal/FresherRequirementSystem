import unittest
from backend.resume_sections import extract_sections


class SectionExtractionTests(unittest.TestCase):
    def test_titles_descriptions_and_experience_aliases(self):
        text='''PROJECTS
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
        values,evidence=extract_sections(text)
        self.assertEqual(values['Projects'],['Sales Dashboard','Loan Risk Predictor'])
        self.assertEqual(values['Internships'],['Python Developer Intern'])
        self.assertEqual(len(values['Work Experience']),2)
        self.assertEqual(len(values['Achievements']),2)
        self.assertIn('Implemented',evidence['Projects'][0]['description'])
        self.assertEqual(values['Certifications'],['Python Certification'])

    def test_missing_is_unknown_explicit_none_is_empty(self):
        values,_=extract_sections('PROJECTS\nOne Project\nInternships\nNone\nSkills\nPython')
        self.assertEqual(values['Internships'],[])
        self.assertIsNone(values['Achievements'])

    def test_no_section_item_count_or_title_length_caps(self):
        titles=['Project '+str(i)+' '+('A'*160) for i in range(30)]
        values,_=extract_sections('Projects\n'+'\n'.join(titles))
        self.assertEqual(len(values['Projects']),30)

    def test_explicit_project_names_and_company_then_role(self):
        values,_=extract_sections('Projects\nProject Name: Sales Dashboard\nBuilt a SQL dashboard.\nProject Title: Inventory App\nImplemented stock alerts.\nInternships\nExample Labs\nRole: Python Developer Intern\nWorked on APIs.')
        self.assertEqual(values['Projects'],['Sales Dashboard','Inventory App'])
        self.assertEqual(values['Internships'],['Python Developer Intern'])


if __name__=='__main__':unittest.main()
