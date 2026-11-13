"""Job-scoped resume batches backed by the existing JSON state and PDF store."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import uuid

import pymupdf as fitz
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

import backend.app as store
from backend.pipeline.config import FEATURE_VERSION, SCORE_VERSION
from backend.pipeline.missing_values import PROFILE_FIELDS as RAW_PROFILE_FIELDS
from backend.pipeline.ranking import rank_records
from backend.pipeline.schema import NUMERIC_BOUNDS
from backend.pipeline.validation import validate_records
from backend.shortlisting import active_allocation, allocate, allocation_summary, assessed_for_job, capacity_config
from backend.resume_validation import (DEGREE, DEGREES, EMAIL, LIST_FIELDS, NUMERIC_FIELDS, PROFILE_FIELDS,
                                       academic_facts, explicit_skills, issue, profile_sources,
                                       specialization_facts, specialization_key, validate_profile)

router = APIRouter(prefix='/api/batches')
MAX_FILES = int(os.environ.get('INCEPTA_BATCH_MAX_FILES', '30'))
MAX_BYTES = int(os.environ.get('INCEPTA_RESUME_MAX_MB', '15')) * 1024 * 1024
MAX_PAGES = int(os.environ.get('INCEPTA_RESUME_MAX_PAGES', '50'))
ADAPTER_VERSION = 'reference-fallbacks-v1'
TERMINAL = ('ready', 'completed', 'failed')


def new_id(prefix):
    return prefix + uuid.uuid4().hex.upper()


def job_snapshot(job):
    return {key: job[key] for key in ('id', 'title', 'required_skills', 'preferred_degree', 'minimum_cgpa', 'openings')} | {
        'version': job.get('version', 1), **capacity_config(job)}


def prepare_batch_profile(screening, job, corrections=None):
    if corrections is None:
        corrections = screening.get('corrections', {})
    evidence = screening.get('field_evidence', {})
    original = screening['raw_extracted']
    extraction_issues = [item for item in screening.get('extraction_issues', [])
                         if item['field'] != 'Resume' or not screening.get('source_verified')]
    effective, issues, provenance = validate_profile({**original, **corrections}, evidence, extraction_issues, corrections)
    effective['Work Experience'] = original.get('Work Experience')
    for field in LIST_FIELDS[1:]:
        entries = effective[field]
        effective['Number of ' + field] = len(entries) if isinstance(entries, list) else None
    raw = store.raw_record(screening, effective, job)
    defaults = dict(raw)
    blocked_fields = {item['field'] for item in issues if item['blocking']}
    for field in RAW_PROFILE_FIELDS:
        if raw.get(field) is None and field not in blocked_fields and field.removeprefix('Number of ') not in blocked_fields:
            defaults[field] = 0 if field in NUMERIC_BOUNDS else 'Not Provided'
    classifier_record, filled = store.prepared_model_record_for_raw(raw)
    if effective['Skills'] == []:
        classifier_record['Skills'] = 'Not Provided'
        filled['Skills'] = {'value': 'Not Provided', 'method': 'explicit empty skills encoding'}
    # Unknown CGPA stays unknown for job eligibility. Historical CGPA_Eligible is
    # generated from the adapter value exclusively for classifier/scoring parity.
    cgpa = effective['CGPA']
    known_cgpa = isinstance(cgpa, (int, float)) and not any(i['blocking'] and i['field'] == 'CGPA' for i in issues)
    eligibility = bool(cgpa >= job['minimum_cgpa']) if known_cgpa else None
    if not any(item['blocking'] for item in issues):
        valid, errors = validate_records([classifier_record])
        if errors:
            for error in errors[0]['Errors'].split('; '):
                field, _, reason = error.partition(': ')
                issues.append(issue(field, raw.get(field), reason, evidence.get(field, [])))
        else:
            classifier_record = valid[0]
    blocked = any(item['blocking'] for item in issues)
    return {'data': effective, 'field_issues': issues, 'provenance': provenance,
            'model_ready_record': defaults, 'classifier_record': None if blocked else classifier_record,
            'imputed_fields': filled, 'adapter_version': ADAPTER_VERSION,
            'job_checks': {'minimum_cgpa': job['minimum_cgpa'], 'cgpa_eligible': eligibility,
                           'job_version': job.get('version', 1)},
            'route': 'review' if blocked else 'not_assessed',
            'segment': 'Needs Data Review' if blocked else 'Not assessed'}


def possible_duplicates(screening, data):
    def normalized(value):
        return ' '.join(re.findall(r'\w+', str(value or '').casefold()))

    email = str(data.get('Email') or '').strip().casefold()
    name = normalized(data.get('Full Name'))
    results = []
    for other in store.state['screenings'].values():
        if other['id'] == screening['id']:
            continue
        profile = other.get('data', {})
        if EMAIL.fullmatch(email) and email == str(profile.get('Email') or '').strip().casefold():
            signal = 'Matching email'
        elif name and name == normalized(profile.get('Full Name')) and all(
            normalized(data.get(key)) and normalized(data.get(key)) == normalized(profile.get(key))
            for key in ('Degree', 'Specialization')
        ):
            signal = 'Matching name, degree and specialization'
        else:
            continue
        results.append({'application_id': other['id'], 'job_id': other['job_id'], 'reason': signal})
    return results


def finish_batch_extraction(screening, data, local, pages, uncertain, warnings, methods, grouped, gemini, metadata):
    facts, academic_sources, findings = academic_facts(pages)
    raw = dict(data)
    raw.update(facts)
    stated_skills = explicit_skills(pages, store.skill_vocabulary)
    if stated_skills is not None and (raw.get('Skills') is None or stated_skills == []):
        raw['Skills'] = stated_skills
    elif stated_skills:
        raw['Skills'] = list(dict.fromkeys([*raw['Skills'], *stated_skills]))
    if not raw.get('Email'):
        raw['Email'] = next((token.strip('<>();,') for page in pages for token in page.split()
                             if '@' in token and token.strip('<>();,') != '@'), None)
    degrees = {DEGREES[re.sub(r'[.\s]', '', match.group()).casefold()]
               for page in pages for match in re.finditer(DEGREE, page, re.I)}
    specializations = specialization_facts(pages)
    if specializations:
        raw['Specialization'] = next(iter(specializations.values()))[0]
    sources = profile_sources(raw, pages, grouped, gemini, findings)
    sources.update(academic_sources)
    if specializations:
        sources['Specialization'] = list({(source['page'], source['text']): source
                                          for _, evidence in specializations.values() for source in evidence}.values())
    if len(degrees) > 1:
        findings.append(issue('Degree', raw.get('Degree'), 'Multiple degrees appear in the resume. Confirm which degree to assess.',
                              sources['Degree'], provenance='ambiguous'))
    if len(specializations) > 1:
        findings.append(issue('Specialization', raw.get('Specialization'), 'Multiple education specializations were found.',
                              sources['Specialization'], provenance='ambiguous'))
    for field in ('Degree', 'Specialization', *NUMERIC_FIELDS):
        remote = (gemini or {}).get('data', {}).get(field)
        original = facts.get(field, local.get(field))
        if field == 'Specialization' and remote is not None and original is not None:
            local_key, remote_key = specialization_key(original), specialization_key(remote)
            if remote_key == local_key or remote_key in local_key.split(' and '):
                continue
        if remote is not None and original is not None and str(remote).casefold() != str(original).casefold() and remote != original:
            findings.append(issue(field, original, 'The local and Gemini parsers returned different values.',
                                  sources.get(field, []), provenance='ambiguous'))
    for warning in (gemini or {}).get('warnings', []):
        field = warning.partition(':')[0]
        if field in PROFILE_FIELDS and raw.get(field) is None:
            findings.append(issue(field, None, 'Gemini found a possible value without sufficient supporting evidence.',
                                  sources.get(field, []), blocking=field not in ('Email', 'Full Name'),
                                  provenance='unextractable'))
    for field in ('Degree', 'Specialization', *NUMERIC_FIELDS, *LIST_FIELDS):
        matches = [source for source in sources.get(field, [])
                   if any(str(token).strip().casefold() in source['text'].casefold()
                          for token in uncertain.get(source['page'], []) if str(token).strip())]
        if matches:
            findings.append(issue(field, raw.get(field), 'Low-confidence OCR supplied this value. Check the source page.',
                                  matches, provenance='unextractable'))
    unreadable = [page for page, tokens in uncertain.items() if not tokens]
    if unreadable or not any(page.strip() for page in pages):
        findings.append(issue('Resume', None, 'Source text could not be read on one or more pages.',
                              [{'page': page, 'text': ''} for page in unreadable], provenance='unextractable'))
    extracted = {'raw_extracted': raw, 'field_evidence': sources, 'extraction_issues': findings,
                 'extracted_at': store.now(), 'text': '\n\n'.join(pages), 'extraction_methods': methods,
                 'warnings': warnings, 'local_extracted': local,
                 'gemini_extracted': (gemini or {}).get('data'), **metadata}
    with store.LOCK:
        profile = prepare_batch_profile({**screening, **extracted}, store.find_job(screening['job_id']))
        store.update_screening(screening['id'], **extracted, **profile, status='ready', error=None,
                               possible_duplicates=possible_duplicates(screening, profile['data']))


def invalidate_assessment(screening):
    if screening['status'] not in TERMINAL or screening['status'] == 'failed':
        return
    profile = prepare_batch_profile(screening, store.find_job(screening['job_id']))
    screening.update(**profile, probability=None, recruitment_score=None, pipeline_result=None, status='ready',
                     assessed_at=None, run_id=None, assessment_error=None, allocation_run_id=None)


def correct_batch_profile(screening_id, corrections, source_verified=False):
    if (not corrections and not source_verified) or not set(corrections) <= set(PROFILE_FIELDS):
        raise HTTPException(422, 'Submit at least one supported profile field.')
    with store.LOCK:
        screening = store.state['screenings'][screening_id]
        if screening['status'] not in ('ready', 'completed'):
            raise HTTPException(409, 'Wait for extraction to finish before correcting data.')
        previous = screening.get('corrections', {})
        updated = {**previous, **corrections}
        changed = {key: value for key, value in corrections.items() if key not in previous or previous[key] != value}
        if source_verified and not screening.get('text', '').strip() and not any(
            updated.get(field) for field in ('Degree', 'Specialization', 'Skills')
        ):
            raise HTTPException(422, 'Add verifiable profile details from the PDF before clearing the unreadable-source finding.')
        verified = source_verified and not screening.get('source_verified')
        if changed or verified:
            screening.setdefault('correction_history', []).append({
                'changes': {key: {'previous': screening['data'].get(key), 'value': value} for key, value in changed.items()},
                'timestamp': store.now(), 'actor': None, 'source_verified': verified,
            })
            screening.update(corrections=updated, revision=screening.get('revision', 0) + 1, confirmed=True)
            if verified:
                screening['source_verified'] = True
            invalidate_assessment(screening)
            screening['possible_duplicates'] = possible_duplicates(screening, screening['data'])
            refresh_job_ranks(screening['job_id'])
            store.persist()
        return store.screening_response(screening)


def refresh_job_ranks(job_id):
    assessed = assessed_for_job(store.state['screenings'].values(), job_id)
    rank_records([s['pipeline_result'] for s in assessed])


def batch_or_404(batch_id):
    batch = store.state['batches'].get(batch_id)
    if batch is None:
        raise HTTPException(404, 'Resume batch not found.')
    return batch


def batch_response(batch):
    files = []
    for file in batch['files']:
        screening = store.state['screenings'].get(file.get('application_id'), {})
        active = not file.get('duplicate')
        keys = ('status', 'route', 'page', 'total_pages', 'error', 'assessment_error', 'attempts')
        item = {**file, **({key: screening.get(key) for key in keys} if active and screening else {})}
        if active and not screening and file.get('application_id'):
            item.update(status='failed', error='The original application is no longer available.', application_id=None)
        item['retryable'] = bool(active and screening.get('status') == 'failed' and screening.get('retryable', True))
        item['possible_duplicate'] = bool(screening and possible_duplicates(screening, screening.get('data', {})))
        item['partial'] = bool(active and screening.get('raw_extracted') and
                               (screening.get('route') == 'review' or any(
                                   v['status'] == 'absent' for k, v in screening.get('provenance', {}).items()
                                   if k in (*NUMERIC_FIELDS, *LIST_FIELDS, 'Degree', 'Specialization'))))
        files.append(item)
    counts = Counter()
    for file in files:
        status = file['status']
        if file.get('duplicate') or file['possible_duplicate']:
            counts['duplicates'] += 1
        if file.get('duplicate'):
            continue
        if status == 'failed':
            counts['failed'] += 1
        if status in ('ready', 'completed'):
            counts['partial' if file['partial'] else 'extracted'] += 1
            if file['route'] != 'review':
                counts['eligible'] += 1
        if file.get('route') == 'review':
            counts['review'] += 1
    run = store.state['model_runs'].get(batch.get('latest_run'), {})
    job = store.find_job(batch['job_id'])
    active = active_allocation(job['id'], store.state)
    allocation = allocation_summary(list(store.state['screenings'].values()), job, active)
    running = job_running(job['id'])
    extracting = any(f['status'] not in (*TERMINAL, 'duplicate') for f in files)
    return {'id': batch['id'], 'job_id': batch['job_id'], 'created_at': batch['created_at'],
            'job': job_snapshot(job), 'allocation': allocation, 'job_running': running,
            'files': files, 'extracting': extracting,
            'counts': {key: counts[key] for key in ('extracted', 'partial', 'failed', 'eligible', 'review', 'duplicates')},
            'run': {key: run[key] for key in ('id', 'status', 'summary', 'error', 'started_at', 'finished_at', 'errors',
                                             'processed', 'total', 'job', 'threshold', 'qualified', 'allocation') if key in run},
            'can_run': bool(not extracting and counts['eligible'] and not running and
                            (run.get('status') != 'completed' or run.get('fingerprint') != run_fingerprint(batch)))}


@router.get('')
def batches():
    with store.LOCK:
        return {'max_files': MAX_FILES, 'max_mb': MAX_BYTES // (1024 * 1024), 'max_pages': MAX_PAGES,
                'items': [{key: batch[key] for key in ('id', 'job_id', 'created_at')}
                          for batch in reversed(list(store.state['batches'].values()))]}


@router.get('/{batch_id}')
def get_batch(batch_id: str):
    with store.LOCK:
        return store.clean(batch_response(batch_or_404(batch_id)))


@router.get('/{batch_id}/runs')
def get_runs(batch_id: str):
    with store.LOCK:
        batch_or_404(batch_id)
        return store.clean([{k: v for k, v in run.items() if k not in ('profiles', 'outcomes', 'fingerprint')}
                            for run in store.state['model_runs'].values() if run['batch_id'] == batch_id])


def stage_file(file, job_id, batch_id):
    filename = Path((file.filename or 'resume.pdf').replace('\\', '/')).name[:240]
    file.file.seek(0)
    pdf = file.file.read(MAX_BYTES + 1)
    if len(pdf) > MAX_BYTES:
        return {'filename': filename, 'status': 'failed', 'error': 'PDF exceeds the upload size limit.'}
    if not filename.casefold().endswith('.pdf') or not pdf.startswith(b'%PDF-'):
        return {'filename': filename, 'status': 'failed', 'error': 'Only PDF resumes are supported.'}
    file_hash = hashlib.sha256(pdf).hexdigest()
    existing = next((s for s in store.state['screenings'].values()
                     if s['job_id'] == job_id and s.get('file_hash') == file_hash), None)
    if existing:
        return {'filename': filename, 'status': 'duplicate', 'application_id': existing['id'],
                'duplicate': True, 'original_batch_id': existing.get('batch_id')}
    application_id = new_id('RES_')
    failure = None
    try:
        with fitz.open(stream=pdf, filetype='pdf') as doc:
            if doc.is_encrypted:
                failure = 'Password-protected PDFs are not supported.'
            elif not 0 < len(doc) <= MAX_PAGES:
                failure = f'A resume must have between 1 and {MAX_PAGES} pages.'
    except (ValueError, RuntimeError):
        failure = 'This PDF could not be read.'
    (store.UPLOADS / (application_id + '.pdf')).write_bytes(pdf)
    store.state['screenings'][application_id] = {
        'id': application_id, 'candidate_id': new_id('CND_'), 'batch_id': batch_id, 'job_id': job_id,
        'filename': filename, 'file_hash': file_hash, 'created_at': store.now(), 'confirmed': False,
        'data': {}, 'status': 'failed' if failure else 'queued', 'error': failure, 'retryable': not failure,
        'route': 'review' if failure else 'not_assessed', 'segment': 'Needs Data Review' if failure else 'Not assessed',
        'field_issues': [issue('Resume', None, failure, provenance='unextractable')] if failure else [],
        'attempts': 0 if failure else 1,
    }
    return {'filename': filename, 'application_id': application_id}


def stage_batch(job_id, key, files):
    with store.LOCK:
        job = store.find_job(job_id)
        existing = next((batch for batch in store.state['batches'].values()
                         if batch['job_id'] == job_id and batch['upload_key'] == key), None)
        if existing:
            return batch_response(existing), []
        if job['status'] != 'Active':
            raise HTTPException(422, 'Select an active job opening.')
        batch_id = new_id('BAT_')
        items = [stage_file(file, job_id, batch_id) for file in files]
        batch = {'id': batch_id, 'job_id': job_id, 'upload_key': key, 'created_at': store.now(), 'files': items}
        store.state['batches'][batch_id] = batch
        store.persist()
        queued = [item['application_id'] for item in items if 'status' not in item
                  and store.state['screenings'][item['application_id']]['status'] == 'queued']
        return batch_response(batch), queued


def extract_batch(application_ids):
    for application_id in application_ids:
        store.extract_resume(application_id)


@router.post('', status_code=202)
async def upload_batch(request: Request, background_tasks: BackgroundTasks, job_id: str, upload_key: uuid.UUID):
    # Multipart uploads spool to disk. Read and hash one bounded file at a time.
    length = request.headers.get('content-length', '')
    if not length.isdigit():
        raise HTTPException(411, 'Send a multipart request with a content length.')
    if int(length) > MAX_FILES * (MAX_BYTES + 4096):
        raise HTTPException(413, 'The batch exceeds the upload size limit.')
    async with request.form(max_files=MAX_FILES, max_fields=0) as form:
        files = form.getlist('files')
        if not files or any(not isinstance(file, UploadFile) for file in files):
            raise HTTPException(422, 'Choose at least one PDF resume.')
        result, queued = await run_in_threadpool(stage_batch, job_id, str(upload_key), files)
    if queued:
        background_tasks.add_task(extract_batch, queued)
    return result


@router.post('/{batch_id}/files/{application_id}/retry', status_code=202)
def retry_file(batch_id: str, application_id: str, background_tasks: BackgroundTasks):
    with store.LOCK:
        batch = batch_or_404(batch_id)
        screening = store.state['screenings'].get(application_id)
        if not screening or screening.get('batch_id') != batch_id:
            raise HTTPException(404, 'Resume is not in this batch.')
        if screening['status'] == 'failed' and screening.get('retryable', True):
            if store.state['model_runs'].get(batch.get('latest_run'), {}).get('status') == 'running':
                raise HTTPException(409, 'Wait for the current assessment before retrying extraction.')
            screening.setdefault('extraction_attempts', []).append(
                {'attempt': screening.get('attempts', 1), 'error': screening.get('error'), 'timestamp': store.now()})
            store.update_screening(application_id, status='queued', route='not_assessed', segment='Not assessed',
                                   attempts=screening.get('attempts', 1) + 1, revision=screening.get('revision', 0) + 1,
                                   error=None, field_issues=[], page=None, total_pages=None)
            background_tasks.add_task(store.extract_resume, application_id)
        return batch_response(batch)


def batch_screenings(batch):
    return [store.state['screenings'][file['application_id']] for file in batch['files']
            if file.get('application_id') in store.state['screenings'] and not file.get('duplicate')]


def run_fingerprint(batch):
    return [store.find_job(batch['job_id']).get('version', 1), store.recruitment_pipeline.model_version
            if store.artifact else None,
            [[s['id'], s.get('revision', 0), s['status'] == 'failed'] for s in batch_screenings(batch)], 'capacity-v1']


def job_running(job_id):
    return any(run['job']['id'] == job_id and run['status'] == 'running' for run in store.state['model_runs'].values())


def infer_isolated(records):
    if not records:
        return [], {}
    try:
        scored, rejected = store.recruitment_pipeline.process_records(records, strict=False)
        return scored, {row['Application ID']: row['Errors'] for row in rejected}
    except Exception as exc:
        logging.warning('Batch model processing failed (%s)', type(exc).__name__)
        if len(records) == 1:
            return [], {records[0]['Application ID']: 'The model could not assess this profile. Retry the batch.'}
        middle = len(records) // 2
        left, left_errors = infer_isolated(records[:middle])
        right, right_errors = infer_isolated(records[middle:])
        return left + right, left_errors | right_errors


def run_assessment(batch_id, run_id, screenings, job):
    try:
        assess_profiles(batch_id, run_id, screenings, job)
    except Exception as exc:
        logging.error('Batch assessment failed (%s)', type(exc).__name__)
        with store.LOCK:
            run = store.state['model_runs'][run_id]
            run.update(status='failed', error='Assessment could not finish. Run the batch again.', finished_at=store.now())
            store.persist()


def assess_profiles(batch_id, run_id, screenings, job):
    prepared, preparation_errors = {}, {}
    for screening in screenings:
        try:
            prepared[screening['id']] = prepare_batch_profile(screening, job)
        except Exception as exc:
            logging.warning('Batch profile preparation failed (%s)', type(exc).__name__)
            preparation_errors[screening['id']] = 'The model inputs could not be prepared. Retry the batch.'
    records = [profile['classifier_record'] for profile in prepared.values() if profile['route'] != 'review']
    scored, errors = [], dict(preparation_errors)
    for start in range(0, len(records), 32):
        chunk = records[start:start + 32]
        results, failures = infer_isolated(chunk)
        scored.extend(results)
        errors.update(failures)
        with store.LOCK:
            run = store.state['model_runs'][run_id]
            run.update(processed=start + len(chunk), total=len(records))
            store.persist()
    outcomes = {record['Application ID']: record for record in scored}
    with store.LOCK:
        batch = batch_or_404(batch_id)
        run = store.state['model_runs'][run_id]
        finished = store.now()
        if run['fingerprint'] != run_fingerprint(batch) or any(
            store.state['screenings'][s['id']].get('revision', 0) != s.get('revision', 0) for s in screenings
        ):
            run.update(status='superseded', finished_at=finished, error='Profile or job data changed. Run the batch again.')
            store.persist()
            return
        for application_id, profile in prepared.items():
            screening = store.state['screenings'][application_id]
            result = outcomes.get(application_id)
            if result:
                screening.update(**profile, status='completed', run_id=run_id, assessed_at=finished,
                                 probability=result['Model_Score'], recruitment_score=result['Recruitment_Score'],
                                 pipeline_result=dict(result), assessment_error=None)
                screening.update(route='pool', segment=result['Model_Segment'])
            else:
                screening.update(**profile, status='ready', run_id=run_id, assessment_error=errors.get(application_id),
                                 probability=None, recruitment_score=None, pipeline_result=None, assessed_at=None)
        for application_id, error in preparation_errors.items():
            store.state['screenings'][application_id].update(status='ready', run_id=run_id, assessment_error=error,
                                                              probability=None, recruitment_score=None, pipeline_result=None,
                                                              assessed_at=None, route='not_assessed', segment='Not assessed')
        pool = assessed_for_job(store.state['screenings'].values(), job['id'])
        selected = allocate(pool, job, run_id)
        active = {'run_id': run_id, 'job': job, 'timestamp': finished, 'enforced': True}
        store.state['job_allocations'][job['id']] = active
        allocation = allocation_summary(list(store.state['screenings'].values()), job, active)
        batch_ids = {s['id'] for s in batch_screenings(batch)}
        batch_results = batch_ids & outcomes.keys()
        shortlist = len(batch_results & set(selected))
        excluded = sum(prepared[app_id]['route'] == 'review' for app_id in batch_ids & prepared.keys())
        for s in pool:
            if s['id'] in outcomes:
                outcomes[s['id']] = {**s['pipeline_result'], 'Shortlist_Selected': s['route'] == 'shortlist'}
        run.update(status='partial' if errors else 'completed', finished_at=finished, errors=errors,
                   profiles=prepared, outcomes=outcomes,
                   qualified=sum(outcomes[app_id]['Model_Prediction'] for app_id in batch_results),
                   allocation={**allocation, 'shortlisted_ids': selected},
                   summary={'assessed': len(batch_results), 'shortlisted': shortlist, 'non_shortlisted': len(batch_results) - shortlist,
                            'failed': len(batch_ids & errors.keys()),
                            'excluded': excluded + run['failed_extraction']})
        store.persist()


@router.post('/{batch_id}/run', status_code=202)
def start_run(batch_id: str, background_tasks: BackgroundTasks):
    with store.LOCK:
        if not store.artifact:
            raise HTTPException(503, 'The saved model is unavailable.')
        batch = batch_or_404(batch_id)
        screenings = batch_screenings(batch)
        if any(s['status'] not in TERMINAL for s in screenings):
            raise HTTPException(409, 'Wait for extraction to finish.')
        fingerprint = run_fingerprint(batch)
        latest = store.state['model_runs'].get(batch.get('latest_run'), {})
        if latest.get('status') == 'running' or (latest.get('status') == 'completed' and latest['fingerprint'] == fingerprint):
            return batch_response(batch)
        if job_running(batch['job_id']):
            raise HTTPException(409, 'An assessment is already running for this position.')
        if not any(s['status'] in ('ready', 'completed') and s['route'] != 'review' for s in screenings):
            raise HTTPException(422, 'No profiles are ready for assessment.')
        job = job_snapshot(store.find_job(batch['job_id']))
        own_ids = {s['id'] for s in screenings}
        # Openings and other job features affect inference. Refresh assessed applications
        # from other batches when their actual model inputs differ from this configuration.
        job_features = {'Number of Openings': job['openings'], 'Minimum CGPA': job['minimum_cgpa'], 'Job Role': job['title'],
                        'Required Skills': ', '.join(job['required_skills']), 'Preferred Degree': ', '.join(job['preferred_degree'])}
        previous = assessed_for_job(store.state['screenings'].values(), job['id'])
        to_assess = [s for s in screenings if s['status'] != 'failed']
        to_assess.extend(s for s in previous if s['id'] not in own_ids and any(
            s['pipeline_result'].get(key) != value for key, value in job_features.items()))
        run_id = new_id('RUN_')
        store.state['model_runs'][run_id] = {
            'id': run_id, 'batch_id': batch_id, 'job': job, 'fingerprint': fingerprint,
            'status': 'running', 'started_at': store.now(), 'adapter_version': ADAPTER_VERSION,
            'model_hash': store.recruitment_pipeline.model_version, 'threshold': float(store.artifact['threshold']),
            'model_name': store.artifact['model_name'], 'feature_columns': store.artifact['feature_columns'],
            'feature_version': FEATURE_VERSION, 'score_version': SCORE_VERSION,
            'failed_extraction': sum(s['status'] == 'failed' for s in screenings),
            'processed': 0, 'total': sum(s['route'] != 'review' for s in to_assess),
        }
        batch['latest_run'] = run_id
        store.persist()
        background_tasks.add_task(run_assessment, batch_id, run_id, deepcopy(to_assess), job)
        return batch_response(batch)
