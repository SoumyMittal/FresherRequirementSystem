"""Local V1. CSV-backed reference data; JSON-backed prototype changes. No database."""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import os
import re
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

# Keep CPU inference small enough for a laptop alongside the browser.
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import pymupdf as fitz
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backend.pipeline import RecruitmentPipeline
from backend.pipeline.config import MAXIMA
from backend.pipeline.schema import RAW_COLUMNS
from backend.pipeline.feature_engineering import make_features
from backend.gemini_parser import extract_with_gemini, parser_status, GeminiError

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / '.runtime'
UPLOADS = RUNTIME / 'uploads'
STATE_FILE = RUNTIME / 'state.json'
CSV_FILE = ROOT / 'AI_Fresher_Recruitment_ML_Dataset.csv'
MAX_UPLOAD = 10 * 1024 * 1024
MAX_PAGES = 15
LOCK = threading.RLock()
OCR_LOCK = threading.Lock()
EXTRACTION_SLOTS = threading.Semaphore(2)
state: dict = {'jobs': {}, 'screenings': {}, 'reviews': {}}
dataset = pd.DataFrame()
artifact = None
recruitment_pipeline = None
model_error = None
ocr_engine = None
model_predictions: dict[str, float] = {}
model_recruitment_scores: dict[str, float] = {}
raw_columns: list[str] = []
normalizers: dict[str, float] = {}
skill_vocabulary: list[str] = []


def clean(value):
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return None
    if hasattr(value, 'item'):
        return clean(value.item())
    return value


def persist():
    with LOCK:
        RUNTIME.mkdir(exist_ok=True)
        temp = STATE_FILE.with_suffix('.tmp')
        temp.write_text(json.dumps(clean(state), indent=2, allow_nan=False), encoding='utf-8')
        os.replace(temp, STATE_FILE)


def initialize():
    global dataset, artifact, model_error, raw_columns, normalizers, skill_vocabulary, recruitment_pipeline
    UPLOADS.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(CSV_FILE).fillna('')
    raw_columns = list(RAW_COLUMNS)
    normalizers = dict(MAXIMA)
    skill_vocabulary = sorted({s.strip() for value in dataset['Skills'] for s in str(value).split(',') if s.strip()}, key=len, reverse=True)
    if STATE_FILE.exists():
        loaded = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        for key in state:
            state[key] = loaded.get(key, {})
    for screening in state['screenings'].values():
        if screening['status'] in ('queued', 'extracting_text', 'ocr', 'parsing', 'structuring', 'checking_fields'):
            screening.update(status='failed', error='Processing was interrupted. Please upload the resume again.')
    try:
        recruitment_pipeline = RecruitmentPipeline()
        artifact = recruitment_pipeline.artifact
        artifact['pipeline'].predict_proba(dataset[artifact['feature_columns']].head(1))
        model_error = None
    except Exception as exc:
        artifact = None
        model_error = f'Model could not be loaded ({type(exc).__name__}). Check the installed training dependencies.'
        logging.exception('Model initialization failed')


@asynccontextmanager
async def lifespan(app):
    initialize()
    yield


app = FastAPI(title='Sprout · Fresher Recruitment V1', lifespan=lifespan)


class JobInput(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    required_skills: list[str] = Field(min_length=1, max_length=50)
    preferred_degree: list[str] = Field(min_length=1, max_length=20)
    minimum_cgpa: float = Field(ge=0, le=10)
    openings: int = Field(ge=1, le=10000)
    status: str = 'Active'


def jobs_list():
    cols = ['Job ID', 'Job Role', 'Number of Openings', 'Required Skills', 'Preferred Degree', 'Minimum CGPA']
    jobs = {}
    for row in dataset[cols].drop_duplicates('Job ID').to_dict('records'):
        jobs[row['Job ID']] = {'id': row['Job ID'], 'title': row['Job Role'], 'openings': int(row['Number of Openings']),
                              'required_skills': split_list(row['Required Skills']), 'preferred_degree': split_list(row['Preferred Degree']),
                              'minimum_cgpa': float(row['Minimum CGPA']), 'status': 'Active'}
    jobs.update(state['jobs'])
    for job in jobs.values():
        job['applications'] = int((dataset['Job ID'] == job['id']).sum()) + sum(s['job_id'] == job['id'] for s in state['screenings'].values())
    return list(jobs.values())


def find_job(job_id):
    job = next((j for j in jobs_list() if j['id'] == job_id), None)
    if not job:
        raise HTTPException(404, 'Job opening not found.')
    return job


def split_list(value):
    if isinstance(value, list):
        return list(dict.fromkeys(str(s).strip() for s in value if str(s).strip()))
    if value is None or str(value).strip().lower() in ('', 'none', 'nan', 'n, o, n, e'):
        return []
    return list(dict.fromkeys(s.strip() for s in str(value).split(',') if s.strip()))


def segment(probability):
    return 'Potential Match' if probability >= float(artifact['threshold']) else 'Lower Model Match'


def candidate_rows(job_id='', query='', selected_segment='', review=''):
    frame = dataset
    if job_id:
        frame = frame[frame['Job ID'] == job_id]
    rows = []
    for r in frame.to_dict('records'):
        app_id = r['Application ID']
        probability = model_predictions.get(app_id)
        rows.append({'id': app_id, 'candidate_id': r['Candidate ID'], 'name': r['Candidate ID'], 'job_id': r['Job ID'],
                     'job': r['Job Role'], 'degree': r['Degree'], 'specialization': r['Specialization'], 'cgpa': r['CGPA'],
                     'skills': split_list(r['Skills']), 'score': float(r['Recruitment_Score']), 'probability': probability,
                     'segment': segment(probability) if probability is not None else ('Dataset Shortlist' if int(r['Shortlisted']) else 'Dataset Pool'),
                     'recruitment_score': model_recruitment_scores.get(app_id) if probability is not None else None,
                     'source': 'ML dataset', 'review': state['reviews'].get(app_id, 'Pending')})
    jobs = {j['id']: j for j in jobs_list()}
    for s in state['screenings'].values():
        if job_id and s['job_id'] != job_id:
            continue
        d = s.get('data', {})
        rows.append({'id': s['id'], 'candidate_id': s['candidate_id'], 'name': d.get('Full Name') or s['candidate_id'],
                     'job_id': s['job_id'], 'job': jobs[s['job_id']]['title'], 'degree': d.get('Degree'),
                     'specialization': d.get('Specialization'), 'cgpa': d.get('CGPA'), 'skills': split_list(d.get('Skills')),
                     'score': None, 'recruitment_score': s.get('recruitment_score') if s.get('confirmed') and s.get('probability') is not None else None,
                     'probability': s.get('probability'), 'segment': s.get('segment', 'Needs Data Review'),
                     'source': 'Resume upload', 'review': state['reviews'].get(s['id'], 'Pending'), 'status': s['status']})
    if query:
        needle = query.casefold()
        rows = [r for r in rows if needle in ' '.join(str(r.get(k, '')) for k in ['name', 'id', 'job', 'degree', 'skills']).casefold()]
    if selected_segment:
        rows = [r for r in rows if r['segment'] == selected_segment]
    if review:
        rows = [r for r in rows if r['review'] == review]
    rows.sort(key=lambda r: (r['probability'] if r['probability'] is not None else -1, r['score'] if r['score'] is not None else -1, r['id']), reverse=True)
    return rows


@app.get('/api/health')
def health():
    return {'ok': True, 'dataset': CSV_FILE.name, 'rows': len(dataset), 'model_ready': artifact is not None,
            'model_error': model_error, 'model_name': artifact['model_name'] if artifact else None,
            'threshold': float(artifact['threshold']) if artifact else None, 'mode': 'Local prototype · mocked login',
            **parser_status()}


@app.get('/api/summary')
def summary():
    jobs = jobs_list()
    by_job = [{'id': j['id'], 'title': j['title'], 'total': j['applications'], 'openings': j['openings'],
               'shortlisted': int(dataset.loc[dataset['Job ID'] == j['id'], 'Shortlisted'].sum())} for j in jobs]
    return clean({'applications': len(dataset) + len(state['screenings']), 'candidates': dataset['Candidate ID'].nunique() + len(state['screenings']),
                  'openings': sum(j['openings'] for j in jobs if j['status'] == 'Active'), 'active_jobs': sum(j['status'] == 'Active' for j in jobs),
                  'dataset_shortlisted': int(dataset['Shortlisted'].sum()), 'average_score': round(float(dataset['Recruitment_Score'].mean()), 1),
                  'uploads': len(state['screenings']), 'reviewed': len([v for v in state['reviews'].values() if v != 'Pending']),
                  'by_job': by_job, 'model_predictions': len(model_predictions),
                  'segments': [{'name': name, 'count': sum(s.get('segment') == name for s in state['screenings'].values())}
                               for name in ['Needs Data Review', 'Potential Match', 'Lower Model Match']]})


@app.get('/api/jobs')
def get_jobs():
    return clean(jobs_list())


@app.post('/api/jobs')
def create_job(payload: JobInput):
    job_id = 'JOB_' + uuid.uuid4().hex[:8].upper()
    return save_job(job_id, payload)


def save_job(job_id, payload):
    if payload.status not in ('Active', 'Closed', 'Draft'):
        raise HTTPException(422, 'Invalid opening status.')
    skills = split_list(payload.required_skills)
    degrees = split_list(payload.preferred_degree)
    if not skills or not degrees or not payload.title.strip():
        raise HTTPException(422, 'Title, required skills, and preferred degrees cannot be blank.')
    job = {'id': job_id, 'title': payload.title.strip(), 'openings': payload.openings, 'required_skills': skills,
           'preferred_degree': degrees, 'minimum_cgpa': payload.minimum_cgpa, 'status': payload.status}
    with LOCK:
        state['jobs'][job_id] = job
        for s in state['screenings'].values():
            if s['job_id'] == job_id:
                s.update(confirmed=False, probability=None, segment='Needs Data Review')
        for app_id in dataset.loc[dataset['Job ID'] == job_id, 'Application ID']:
            model_predictions.pop(app_id, None)
            model_recruitment_scores.pop(app_id, None)
        persist()
    return job


@app.put('/api/jobs/{job_id}')
def update_job(job_id: str, payload: JobInput):
    find_job(job_id)
    return save_job(job_id, payload)


@app.get('/api/candidates')
def get_candidates(job_id: str = '', q: str = '', segment: str = '', review: str = '', page: int = 1, limit: int = 12, sort: str = ''):
    rows = candidate_rows(job_id, q, segment, review)
    if sort == 'dataset':
        rows.sort(key=lambda r: (r['score'] if r['score'] is not None else -1, r['id']), reverse=True)
    limit = min(max(limit, 1), 100)
    page = max(page, 1)
    start = (page - 1) * limit
    return clean({'items': rows[start:start + limit], 'total': len(rows), 'page': page, 'pages': max(1, math.ceil(len(rows) / limit))})


@app.get('/api/export')
def export(job_id: str = '', q: str = '', segment: str = '', review: str = ''):
    rows = candidate_rows(job_id, q, segment, review)
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['Application ID', 'Candidate', 'Job Role', 'Degree', 'CGPA', 'Dataset Score', 'Recruitment Score', 'Model Score', 'Segment', 'HR Review', 'Source'])
    for r in rows:
        values = [r['id'], r['name'], r['job'], r['degree'], r['cgpa'], r['score'], r.get('recruitment_score'), r['probability'], r['segment'], r['review'], r['source']]
        writer.writerow(["'" + str(v) if isinstance(v, str) and v.startswith(('=', '+', '-', '@')) else v for v in values])
    return Response('\ufeff' + out.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="sprout-candidates.csv"'})


@app.get('/api/candidates/{application_id}')
def detail(application_id: str):
    if application_id in state['screenings']:
        return screening_response(state['screenings'][application_id])
    frame = dataset[dataset['Application ID'] == application_id]
    if frame.empty:
        raise HTTPException(404, 'Application not found.')
    r = frame.iloc[0].to_dict()
    probability = model_predictions.get(application_id)
    return clean({'id': application_id, 'data': r, 'source': 'ML dataset', 'confirmed': True, 'status': 'completed',
                  'probability': probability, 'segment': segment(probability) if probability is not None else ('Dataset Shortlist' if int(r['Shortlisted']) else 'Dataset Pool'),
                  'review': state['reviews'].get(application_id, 'Pending'), 'warnings': [], 'job_id': r['Job ID'],
                  'recruitment_score': model_recruitment_scores.get(application_id) if probability is not None else None})


class ReviewInput(BaseModel):
    status: str


@app.patch('/api/candidates/{application_id}/review')
def review_candidate(application_id: str, payload: ReviewInput):
    detail(application_id)
    if payload.status not in ('Pending', 'Reviewed', 'Shortlisted', 'Not progressing'):
        raise HTTPException(422, 'Invalid review status.')
    with LOCK:
        state['reviews'][application_id] = payload.status
        persist()
    return {'status': payload.status}


def update_screening(screening_id, **changes):
    with LOCK:
        if 'status' in changes:
            history=state['screenings'][screening_id].setdefault('stage_history', [])
            if changes['status'] not in history:
                history.append(changes['status'])
        state['screenings'][screening_id].update(changes)
        persist()


def extract_resume(screening_id):
    # Multiple uploaded documents keep independent statuses; limit heavy OCR/model parsers.
    with EXTRACTION_SLOTS:
        _extract_resume(screening_id)


def _extract_resume(screening_id):
    global ocr_engine
    try:
        path = UPLOADS / (screening_id + '.pdf')
        update_screening(screening_id, status='extracting_text')
        texts, methods, warnings = [], [], []
        with fitz.open(path) as doc:
            update_screening(screening_id, total_pages=len(doc))
            for i, page in enumerate(doc):
                update_screening(screening_id, status='extracting_text', page=i+1)
                text = page.get_text(sort=True)
                if len(re.sub(r'\s', '', text)) < 40:
                    update_screening(screening_id, status='ocr', page=i + 1)
                    with OCR_LOCK:
                        if ocr_engine is None:
                            from rapidocr_onnxruntime import RapidOCR
                            ocr_engine = RapidOCR(det_use_cuda=False, cls_use_cuda=False, rec_use_cuda=False,
                                                  intra_op_num_threads=2, inter_op_num_threads=2)
                        scale = min(1.8, 1400 / max(page.rect.width, page.rect.height))
                        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                        result, _ = ocr_engine(pix.tobytes('png'))
                    text = '\n'.join(item[1] for item in (result or []))
                    methods.append(f'Page {i + 1}: OCR')
                    if result and any(float(item[2]) < 0.8 for item in result):
                        warnings.append(f'Page {i + 1} contains uncertain OCR text. Check it against the PDF.')
                else:
                    methods.append(f'Page {i + 1}: embedded text')
                texts.append(text)
        text = '\n\n'.join(texts)
        if len(text.strip()) < 15:
            raise ValueError('No readable text was found. Please use a clearer PDF.')
        update_screening(screening_id, status='parsing')
        data = parse_resume(text)
        parser_metadata = {'parser': 'local', 'parser_model': None, 'evidence': {}}
        if parser_status()['gemini_configured']:
            try:
                update_screening(screening_id, status='structuring')
                result = extract_with_gemini(text)
                data = result['data']
                warnings.extend(result['warnings'])
                parser_metadata = {key: result[key] for key in ('parser', 'parser_model', 'evidence')}
            except GeminiError as exc:
                warnings.append(str(exc) + ' Local parsing was used instead; review all fields.')
        warnings.append('Extraction is a draft. Confirm grades, backlog information, and section entries before prediction.')
        update_screening(screening_id, status='checking_fields')
        validation_issues = validate_confirmed(dict(data))
        update_screening(screening_id, status='ready', data=data, text=text, extraction_methods=methods,
                         warnings=warnings, validation_issues=validation_issues, segment='Needs Data Review', error=None, **parser_metadata)
    except Exception as exc:
        logging.exception('Resume extraction failed')
        message = str(exc) if isinstance(exc, ValueError) else 'Resume extraction failed. Check OCR dependencies and try again.'
        update_screening(screening_id, status='failed', error=message)


def parse_resume(text):
    def search(pattern):
        match = re.search(pattern, text, re.I)
        return match.group(1).strip() if match else None

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = next((line for line in lines[:4] if re.fullmatch(r'[A-Za-z .\-]{3,60}', line) and not re.search(r'resume|curriculum|vitae|profile', line, re.I)), None)
    cgpa = search(r'(?:CGPA|GPA)\s*[:=\-]?\s*(\d+(?:\.\d+)?)')
    if cgpa and float(cgpa) > 10:
        cgpa = None
    scale = search(r'(?:CGPA|GPA)\s*[:=\-]?\s*\d+(?:\.\d+)?\s*(?:/|out of)\s*(\d+(?:\.\d+)?)')
    if scale and float(scale) != 10:
        cgpa = None
    def school_percentage(label):
        value = search(label + r'\s*(?:percentage|marks|score)?\s*[:=\-]?\s*(\d+(?:\.\d+)?)\s*%')
        return float(value) if value is not None and 0 <= float(value) <= 100 else None
    degree_raw = search(r'\b(B\.?\s?Tech|B\.?\s?E\.?|B\.?\s?Sc\.?|BCA|MCA|M\.?\s?Tech|M\.?\s?Sc\.?)\b')
    degree_key = re.sub(r'[.\s]', '', degree_raw or '').lower()
    degree = {'btech': 'B.Tech', 'be': 'B.E', 'bsc': 'B.Sc', 'bca': 'BCA', 'mca': 'MCA', 'mtech': 'M.Tech', 'msc': 'M.Sc'}.get(degree_key)
    found_skills = []
    for skill in skill_vocabulary:
        if re.search(r'(?<![\w])' + re.escape(skill) + r'(?![\w+#])', text, re.I):
            found_skills.append(skill)
    specialization = search(r'\b(Computer Science(?: and Engineering)?|Information Technology|Artificial Intelligence|Data Science|Electronics(?: and Communication)?|Mechanical Engineering)\b')
    backlogs = search(r'backlogs?\s*[:=\-]?\s*(\d+)')
    sections = {'Projects': [], 'Internships': [], 'Certifications': [], 'Achievements': []}
    heading_map = {'projects': 'Projects', 'academic projects': 'Projects', 'personal projects': 'Projects',
                   'internships': 'Internships', 'internship experience': 'Internships', 'certifications': 'Certifications',
                   'certificates': 'Certifications', 'achievements': 'Achievements', 'awards': 'Achievements'}
    current = None
    explicitly_empty = set()
    for line in lines:
        if re.search(r'FICTIONAL TEST RESUME|Not a real applicant|Incepta prototype', line, re.I) or line.isdigit():
            continue
        heading = re.sub(r'[^a-z ]', '', line.casefold()).strip()
        if heading in heading_map:
            current = heading_map[heading]
        elif heading in ['education', 'skills', 'technical skills', 'experience', 'work experience', 'summary', 'contact', 'interests']:
            current = None
        elif current and len(line) < 150:
            if re.fullmatch(r'none(?:\s*[-–:]\s*explicitly declared by candidate)?', line, re.I):
                explicitly_empty.add(current)
            else:
                sections[current].append(re.sub(r'^[•\-*\d.)\s]+', '', line))
    data = {'Full Name': name, 'Email': search(r'([\w.+\-]+@[\w.\-]+\.[A-Za-z]{2,})'),
            'Degree': degree, 'Specialization': specialization, 'CGPA': float(cgpa) if cgpa else None,
            'Class 10 Percentage': school_percentage(r'(?:Class\s*(?:10|X)\b|10th\b|SSC\b)'),
            'Class 12 Percentage': school_percentage(r'(?:Class\s*(?:12|XII)\b|12th\b|HSC\b)'),
            'Backlogs': int(backlogs) if backlogs is not None else None,
            'Skills': found_skills or None}
    for key, entries in sections.items():
        data[key] = list(dict.fromkeys(entries)) if entries else ([] if key in explicitly_empty else None)
        # Draft section lines may include descriptions. Counts require explicit HR confirmation.
    return data


def screening_response(s):
    result = {k: v for k, v in s.items() if k != 'text'}
    result['text'] = s.get('text', '')
    result['source'] = 'Resume upload'
    result['review'] = state['reviews'].get(s['id'], 'Pending')
    result['job'] = find_job(s['job_id'])
    return clean(result)


@app.post('/api/screenings')
async def upload(background_tasks: BackgroundTasks, job_id: str, file: UploadFile = File(...)):
    job = find_job(job_id)
    if job['status'] != 'Active':
        raise HTTPException(422, 'Select an active job opening.')
    data = await file.read(MAX_UPLOAD + 1)
    await file.close()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, 'Please upload a PDF smaller than 10 MB.')
    if not data.startswith(b'%PDF-') or not (file.filename or '').lower().endswith('.pdf'):
        raise HTTPException(422, 'Only PDF resumes are supported.')
    try:
        with fitz.open(stream=data, filetype='pdf') as doc:
            if doc.is_encrypted:
                raise ValueError('Password-protected PDFs are not supported.')
            if not 1 <= len(doc) <= MAX_PAGES:
                raise ValueError('Resumes must contain 1–15 pages.')
            if any(page.rect.width * page.rect.height > 4_000_000 for page in doc):
                raise ValueError('PDF page dimensions are too large. Please upload a standard-size PDF.')
    except Exception as exc:
        raise HTTPException(422, str(exc) if isinstance(exc, ValueError) else 'This PDF could not be read.') from exc
    screening_id = 'RES_' + uuid.uuid4().hex[:12].upper()
    (UPLOADS / (screening_id + '.pdf')).write_bytes(data)
    with LOCK:
        state['screenings'][screening_id] = {'id': screening_id, 'candidate_id': 'CND_' + uuid.uuid4().hex[:8].upper(),
                                            'job_id': job_id, 'filename': Path(file.filename).name, 'status': 'queued',
                                            'confirmed': False, 'data': {}, 'warnings': [], 'segment': 'Needs Data Review',
                                            'created_at': datetime.now(timezone.utc).isoformat()}
        persist()
    background_tasks.add_task(extract_resume, screening_id)
    return {'id': screening_id, 'status': 'queued'}


@app.get('/api/screenings/{screening_id}')
def get_screening(screening_id: str):
    s = state['screenings'].get(screening_id)
    if not s:
        raise HTTPException(404, 'Resume screening not found.')
    return screening_response(s)


@app.get('/api/screenings/{screening_id}/resume')
def get_resume(screening_id: str):
    get_screening(screening_id)
    return FileResponse(UPLOADS / (screening_id + '.pdf'), media_type='application/pdf', headers={'Content-Disposition': 'inline'})


class DataInput(BaseModel):
    data: dict


NUMERIC_FIELDS = ['CGPA', 'Class 10 Percentage', 'Class 12 Percentage', 'Backlogs']
LIST_FIELDS = ['Skills', 'Projects', 'Internships', 'Certifications', 'Achievements']


def validate_confirmed(data):
    errors = []
    for key in ['Degree', 'Specialization'] + NUMERIC_FIELDS + LIST_FIELDS:
        if key not in data or data[key] is None or data[key] == '':
            errors.append(f'{key} is missing. Enter a confirmed value.')
    for key in NUMERIC_FIELDS:
        value = data.get(key)
        if value is None or value == '':
            continue
        try:
            number = float(value)
            upper = 10 if key == 'CGPA' else (100 if 'Percentage' in key else 1000)
            if not math.isfinite(number) or not 0 <= number <= upper or (key == 'Backlogs' and not number.is_integer()):
                raise ValueError()
            data[key] = int(number) if key == 'Backlogs' else number
        except (ValueError, TypeError):
            errors.append(f'{key} has an invalid value.')
    for key in LIST_FIELDS:
        if data.get(key) is not None:
            data[key] = split_list(data[key])
    if not split_list(data.get('Skills')):
        errors.append('At least one confirmed skill is required.')
    return errors


@app.put('/api/screenings/{screening_id}/data')
def confirm_data(screening_id: str, payload: DataInput):
    s = get_screening(screening_id)
    if s['status'] not in ('ready', 'completed'):
        raise HTTPException(409, 'Wait for extraction to finish before confirming data.')
    data = {k: v for k, v in payload.data.items() if k in ['Full Name', 'Email', 'Degree', 'Specialization'] + NUMERIC_FIELDS + LIST_FIELDS}
    errors = validate_confirmed(data)
    if errors:
        update_screening(screening_id, data=data, confirmed=False, probability=None, segment='Needs Data Review')
        raise HTTPException(422, {'message': 'Please complete the required model inputs.', 'fields': errors})
    update_screening(screening_id, data=data, confirmed=True, probability=None, segment='Needs Data Review', status='ready')
    return get_screening(screening_id)


def raw_record(s, data=None):
    d = s['data'] if data is None else data
    job = find_job(s['job_id'])
    r = {'Application ID': s['id'], 'Candidate ID': s['candidate_id'], 'Job ID': job['id'], 'Job Role': job['title'],
         'Degree': d.get('Degree'), 'Specialization': d.get('Specialization'), **{k: d.get(k) for k in NUMERIC_FIELDS},
         'Number of Openings': job['openings'], 'Required Skills': ', '.join(job['required_skills']),
         'Preferred Degree': ', '.join(job['preferred_degree']), 'Minimum CGPA': job['minimum_cgpa']}
    for key in LIST_FIELDS:
        entries = split_list(d.get(key))
        r[key] = (', '.join(entries) if entries else 'None') if d.get(key) is not None else None
        if key != 'Skills':
            r['Number of ' + key] = len(entries) if d.get(key) is not None else None
    return r


class ScreeningExport(BaseModel):
    screening_ids: list[str] = Field(min_length=1, max_length=100)
    mode: str = 'model'


@app.post('/api/screenings/export-csv')
def export_screenings(payload: ScreeningExport):
    if payload.mode not in ('model', 'draft'):
        raise HTTPException(422, 'Export mode must be model or draft.')
    if len(payload.screening_ids) != len(set(payload.screening_ids)):
        raise HTTPException(422, 'Each application must be selected only once.')
    records = []
    for screening_id in payload.screening_ids:
        s = get_screening(screening_id)
        if s['status'] not in ('ready', 'completed'):
            raise HTTPException(409, 'Wait for extraction to finish; failed documents cannot be exported.')
        if payload.mode == 'model' and not s.get('confirmed'):
            raise HTTPException(409, 'Review and confirm every selected resume before downloading model-ready data.')
        records.append(raw_record(s))
    if payload.mode == 'model':
        from backend.pipeline.validation import validate_records
        valid, errors = validate_records(records)
        if errors:
            raise HTTPException(422, {'message':'Some application fields need review.', 'fields':[row['Errors'] for row in errors]})
        records = valid
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=RAW_COLUMNS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(records)
    filename = 'Incepta_Applications.csv' if payload.mode == 'model' else 'Incepta_Extraction_Draft.csv'
    return Response('\ufeff' + stream.getvalue(), media_type='text/csv',
                    headers={'Content-Disposition':f'attachment; filename="{filename}"',
                             'X-CSV-Status':'model-ready' if payload.mode == 'model' else 'draft-needs-review'})


def model_mapping(s, data=None):
    if not artifact:
        raise HTTPException(503, model_error or 'Model unavailable.')
    record = raw_record(s, data)
    from backend.pipeline.validation import validate_records
    valid, invalid = validate_records([record])
    if invalid:
        raise HTTPException(422, invalid[0]['Errors'])
    features = make_features(valid[0])
    return {'raw_record': clean({key: valid[0][key] for key in raw_columns}),
            'model_inputs': clean({key: features[key] for key in artifact['feature_columns']}),
            'feature_count': len(artifact['feature_columns']), 'normalization_constants': normalizers,
            'model_name': artifact['model_name'], 'threshold': float(artifact['threshold']),
            'excluded_fields': ['Full Name', 'Email', 'Application ID', 'Candidate ID', 'Job ID']}


@app.post('/api/screenings/{screening_id}/input-preview')
def preview_inputs(screening_id: str, payload: DataInput):
    s = get_screening(screening_id)
    if s['status'] not in ('ready', 'completed'):
        raise HTTPException(409, 'Wait for extraction to finish before checking model inputs.')
    data = dict(payload.data)
    errors = validate_confirmed(data)
    if errors:
        raise HTTPException(422, {'message': 'Complete the model inputs first.', 'fields': errors})
    return model_mapping(s, data)


@app.post('/api/candidates/{application_id}/predict')
def predict(application_id: str):
    if not artifact:
        raise HTTPException(503, model_error or 'Model unavailable.')
    if application_id in state['screenings']:
        s = state['screenings'][application_id]
        if not s.get('confirmed'):
            raise HTTPException(409, 'Confirm the extracted data before prediction.')
        raw = raw_record(s)
    else:
        frame = dataset[dataset['Application ID'] == application_id]
        if frame.empty:
            raise HTTPException(404, 'Application not found.')
        job = find_job(dataset.loc[dataset['Application ID'] == application_id, 'Job ID'].iloc[0])
        # Refresh job-dependent inputs if HR edited an opening.
        raw = dataset[dataset['Application ID'] == application_id].iloc[0].to_dict()
        raw.update({'Job Role': job['title'], 'Required Skills': ', '.join(job['required_skills']), 'Preferred Degree': ', '.join(job['preferred_degree']),
                    'Minimum CGPA': job['minimum_cgpa'], 'Number of Openings': job['openings']})
    try:
        scored, _ = recruitment_pipeline.process_records([raw])
        pipeline_result = scored[0]
        probability = pipeline_result['Model_Score']
    except Exception as exc:
        logging.exception('Prediction failed')
        raise HTTPException(503, 'The model could not score this record. Its segment was not changed.') from exc
    result = {'probability': probability, 'segment': segment(probability), 'threshold': float(artifact['threshold']),
              'model_name': artifact['model_name'], 'feature_count': len(artifact['feature_columns']),
              'recruitment_score': pipeline_result['Recruitment_Score'], 'pipeline_result': pipeline_result}
    if application_id in state['screenings']:
        update_screening(application_id, **result, status='completed', model_record=clean(raw))
    else:
        model_predictions[application_id] = probability
        model_recruitment_scores[application_id] = pipeline_result['Recruitment_Score']
    return result


@app.get('/api/screenings/{screening_id}/mapped-data')
def mapped_data(screening_id: str):
    s = get_screening(screening_id)
    if not s['confirmed']:
        raise HTTPException(409, 'Confirm candidate data before exporting model inputs.')
    return model_mapping(s)


@app.post('/api/segments/run')
def segment_dataset(job_id: str = ''):
    if not artifact:
        raise HTTPException(503, model_error or 'Model unavailable.')
    if job_id:
        find_job(job_id)
    frame = dataset[dataset['Job ID'] == job_id].copy() if job_id else dataset.copy()
    if frame.empty:
        return {'processed': 0, 'potential_matches': 0, 'message': 'No reference dataset applications for this opening. Use resume upload to add candidates.'}
    try:
        jobs = {j['id']: j for j in jobs_list()}
        records = frame.to_dict('records')
        for raw in records:
            j = jobs[raw['Job ID']]
            raw.update({'Job Role': j['title'], 'Required Skills': ', '.join(j['required_skills']),
                        'Preferred Degree': ', '.join(j['preferred_degree']), 'Minimum CGPA': j['minimum_cgpa'], 'Number of Openings': j['openings']})
        scored, _ = recruitment_pipeline.process_records(records)
        with LOCK:
            model_predictions.update({r['Application ID']: r['Model_Score'] for r in scored})
            model_recruitment_scores.update({r['Application ID']: r['Recruitment_Score'] for r in scored})
        return {'processed': len(frame), 'potential_matches': sum(r['Model_Prediction'] for r in scored),
                'threshold': float(artifact['threshold'])}
    except Exception as exc:
        logging.exception('Dataset segmentation failed')
        raise HTTPException(503, 'The model could not segment these applications. Please check model compatibility.') from exc


app.mount('/', StaticFiles(directory=ROOT / 'frontend', html=True), name='frontend')
