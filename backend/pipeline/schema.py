import csv

RAW_COLUMNS = (
    'Application ID', 'Candidate ID', 'Job ID', 'Job Role', 'Degree', 'Specialization', 'CGPA',
    'Class 10 Percentage', 'Class 12 Percentage', 'Backlogs', 'Skills', 'Number of Projects', 'Projects',
    'Number of Internships', 'Internships', 'Number of Certifications', 'Certifications',
    'Number of Achievements', 'Achievements', 'Number of Openings', 'Required Skills', 'Preferred Degree', 'Minimum CGPA',
)
IDENTIFIERS = ('Application ID', 'Candidate ID', 'Job ID')
DERIVED_COLUMNS = (
    'CGPA_Score', 'CGPA_Eligible', 'CGPA_Gap', 'Degree_Match', 'Skill_Match', 'Project_Count',
    'Internship_Count', 'Certification_Count', 'Achievement_Count', 'Backlog_Score', 'Project_Score',
    'Internship_Score', 'Certification_Score', 'Achievement_Score',
)
EXPECTED_FEATURES = tuple(c for c in RAW_COLUMNS if c not in IDENTIFIERS) + DERIVED_COLUMNS
NUMERIC_BOUNDS = {'CGPA': (0, 10, False), 'Class 10 Percentage': (0, 100, False),
                  'Class 12 Percentage': (0, 100, False), 'Backlogs': (0, None, True),
                  'Number of Projects': (0, None, True), 'Number of Internships': (0, None, True),
                  'Number of Certifications': (0, None, True), 'Number of Achievements': (0, None, True),
                  'Number of Openings': (1, None, True), 'Minimum CGPA': (0, 10, False)}


def verify_reference(path):
    with open(path, newline='', encoding='utf-8-sig') as source:
        header = next(csv.reader(source))
    if tuple(header[:len(RAW_COLUMNS)]) != RAW_COLUMNS:
        raise ValueError('Reference CSV raw column names/order differ from the versioned 23-column schema.')


def header_errors(header):
    if not header:
        return ['CSV has no header.']
    errors = []
    duplicates = sorted({c for c in header if header.count(c) > 1})
    if duplicates:
        errors.append('Duplicate column names: ' + ', '.join(duplicates))
    missing = [c for c in RAW_COLUMNS if c not in header]
    if missing:
        errors.append('Missing required columns: ' + ', '.join(missing))
    return errors
