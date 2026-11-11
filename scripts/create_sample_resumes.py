"""Generate fictional English PDF test fixtures. Does not upload or seed application storage."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

from backend.pipeline.schema import RAW_COLUMNS
from backend.pipeline.csv_export import write_csv

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'samples' / 'resumes'

PROFILES = [
    {'file':'01_python_developer_text.pdf','name':'Aarav Sample','job':'JOB_004','role':'Python Developer',
     'degree':'B.Tech','specialization':'Computer Science','cgpa':8.6,'ten':89,'twelve':87.5,'backlogs':0,
     'skills':['Python','SQL','Git','Django','Flask','Pandas'],
     'projects':['Student Management System','Expense Tracker'], 'internships':['Python Developer Intern'],
     'certifications':['Python Certification'], 'achievements':['Coding Competition Winner'], 'mode':'text'},
    {'file':'02_ml_engineer_scanned.pdf','name':'Meera Sample','job':'JOB_001','role':'AI/ML Engineer',
     'degree':'B.E','specialization':'Artificial Intelligence','cgpa':9.1,'ten':93,'twelve':91,'backlogs':0,
     'skills':['Python','Machine Learning','SQL','Statistics','Pandas','NumPy','Scikit-Learn','Deep Learning','Git'],
     'projects':['Image Classification','Fake News Detection','Sales Data Analysis'], 'internships':['AI/ML Intern'],
     'certifications':['Machine Learning Certification','Python Certification'], 'achievements':['Department Rank Holder'], 'mode':'scanned'},
    {'file':'03_data_analyst_text.pdf','name':'Kabir Sample','job':'JOB_002','role':'Data Analyst',
     'degree':'BCA','specialization':'Data Science','cgpa':7.2,'ten':76,'twelve':79,'backlogs':1,
     'skills':['Python','SQL','Statistics','Pandas','NumPy','Git'], 'projects':['Sales Data Analysis'],
     'internships':[], 'certifications':['Statistics Certification'], 'achievements':[], 'mode':'text'},
    {'file':'04_missing_academics_text.pdf','name':'Nisha Sample','job':'JOB_003','role':'Software Engineer',
     'degree':'B.Tech','specialization':'Information Technology','cgpa':None,'ten':None,'twelve':None,'backlogs':None,
     'skills':['Java','SQL','Git','DSA'], 'projects':['Bank Management System'], 'internships':None,
     'certifications':None, 'achievements':None, 'mode':'text'},
    {'file':'05_software_engineer_mixed.pdf','name':'Rohan Sample','job':'JOB_003','role':'Software Engineer',
     'degree':'B.Tech','specialization':'Computer Science','cgpa':8.0,'ten':84,'twelve':86,'backlogs':0,
     'skills':['Python','Java','C++','SQL','DSA','Git'], 'projects':['Bank Management System','Student Management System'],
     'internships':['Web Development Intern'], 'certifications':['Python Certification'], 'achievements':['Coding Competition Participant'], 'mode':'mixed'},
]


def build_pdf(profile, sections_only=False):
    buffer = io.BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ResumeName', fontName='Helvetica-Bold', fontSize=26, leading=31, textColor=colors.HexColor('#213d35'), spaceAfter=7))
    styles.add(ParagraphStyle(name='ResumeSection', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor('#355b49'), spaceBefore=15, spaceAfter=8))
    styles.add(ParagraphStyle(name='ResumeText', fontName='Helvetica', fontSize=10, leading=16, spaceAfter=4))
    story = []
    def para(text, style='ResumeText'):
        story.append(Paragraph(text, styles[style]))
    para(profile['name'], 'ResumeName')
    para(profile['role'] + ' | Fresher candidate')
    para(profile['name'].split()[0].lower() + '.sample@example.test')
    story.extend([Spacer(1,10), HRFlowable(width='100%', thickness=1, color=colors.HexColor('#d3dfd0'))])
    if not sections_only:
        para('Education', 'ResumeSection')
        para(profile['degree'] + ' - ' + profile['specialization'])
        para('Fictional Institute of Technology | Graduating 2026')
        if profile['cgpa'] is not None:
            para(f'CGPA: {profile["cgpa"]}/10')
            para(f'Class 10 Percentage: {profile["ten"]}%')
            para(f'Class 12 Percentage: {profile["twelve"]}%')
            para(f'Backlogs: {profile["backlogs"]}')
        para('Skills', 'ResumeSection')
        para(', '.join(profile['skills']))
    if profile['mode'] != 'mixed' or sections_only:
        for key in ('projects','internships','certifications','achievements'):
            if profile[key] is None:
                continue
            para(key.title(), 'ResumeSection')
            if not profile[key]:
                para('None - explicitly declared by candidate')
            for title in profile[key]:
                para(title)
    def page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#7d897a'))
        canvas.drawString(48, 30, 'FICTIONAL TEST RESUME | Not a real applicant | Incepta prototype')
        canvas.drawRightString(A4[0]-48, 30, str(doc.page))
        canvas.restoreState()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=48, leftMargin=48, rightMargin=48)
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return buffer.getvalue()


def rasterize(pdf):
    output = fitz.open()
    with fitz.open(stream=pdf, filetype='pdf') as source:
        for page in source:
            image = page.get_pixmap(matrix=fitz.Matrix(1.8,1.8), alpha=False).tobytes('png')
            target = output.new_page(width=page.rect.width, height=page.rect.height)
            target.insert_image(target.rect, stream=image)
    data = output.tobytes(deflate=True)
    output.close()
    return data


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {}
    import csv
    with (ROOT/'jobs_dataset.csv').open(newline='',encoding='utf-8-sig') as stream:
        jobs = {row['Job ID']:row for row in csv.DictReader(stream)}
    raw_rows, expected = [], []
    for index, profile in enumerate(PROFILES,1):
        data = build_pdf(profile)
        if profile['mode'] == 'scanned':
            data = rasterize(data)
        if profile['mode'] == 'mixed':
            doc = fitz.open(stream=data, filetype='pdf')
            with fitz.open(stream=rasterize(build_pdf(profile, True)), filetype='pdf') as scanned:
                doc.insert_pdf(scanned)
            data = doc.tobytes(deflate=True)
            doc.close()
        (OUT/profile['file']).write_bytes(data)
        job = jobs[profile['job']]
        row = {'Application ID':f'SAMPLE_APP_{index:03}', 'Candidate ID':f'SAMPLE_CND_{index:03}',
               **job, 'Degree':profile['degree'], 'Specialization':profile['specialization'], 'CGPA':profile['cgpa'],
               'Class 10 Percentage':profile['ten'], 'Class 12 Percentage':profile['twelve'], 'Backlogs':profile['backlogs'],
               'Skills':', '.join(profile['skills'])}
        for key in ('projects','internships','certifications','achievements'):
            entries = profile[key]
            row[key.title()] = ', '.join(entries) if entries else 'None' if entries == [] else None
            row['Number of '+key.title()] = len(entries) if entries is not None else None
        raw_rows.append(row)
        expected.append({'filename':profile['file'], 'mode':profile['mode'], 'full_name':profile['name'],
                         'raw_record':row, 'expect_review_required':True, 'expect_prediction_blocked_until_missing_fields_completed':profile['cgpa'] is None})
    write_csv(OUT.parent/'applications_valid.csv', [r for r in raw_rows if r['CGPA'] is not None], RAW_COLUMNS)
    write_csv(OUT.parent/'applications_with_missing.csv', raw_rows, RAW_COLUMNS)
    (OUT.parent/'expected_results.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
    print(f'Created {len(PROFILES)} fictional PDFs and companion CSV fixtures in {OUT.parent}')


if __name__ == '__main__':
    main()
