"""Job capacity and allocation over the current assessed resume pool."""
from decimal import Decimal, ROUND_CEILING

from backend.pipeline.ranking import model_rank_key, rank_records

DEFAULT_RATIO = Decimal('3.5')


def capacity_config(job):
    openings = job['openings']
    ratio = Decimal(str(job.get('shortlisting_ratio', DEFAULT_RATIO)))
    capacity = int((openings * ratio).to_integral_value(rounding=ROUND_CEILING))
    return {'openings': openings, 'shortlisting_ratio': float(ratio), 'shortlist_capacity': capacity}


def assessed_for_job(screenings, job_id):
    return [s for s in screenings if s['job_id'] == job_id and s.get('batch_id')
            and s['status'] == 'completed' and s.get('pipeline_result') and s.get('route') != 'review']


def allocate(screenings, configuration, run_id):
    results = rank_records([s['pipeline_result'] for s in screenings])
    qualifying = sorted((result for result in results if result['Model_Prediction']), key=model_rank_key)
    selected = {result['Application ID'] for result in qualifying[:configuration['shortlist_capacity']]}
    for screening in screenings:
        screening['route'] = 'shortlist' if screening['id'] in selected else 'pool'
        screening['allocation_run_id'] = run_id
    return sorted(selected)


def allocation_summary(screenings, job, active):
    assessed = assessed_for_job(screenings, job['id'])
    shortlisted = sum(s.get('route') == 'shortlist' for s in assessed)
    qualifying = sum(s['pipeline_result']['Model_Prediction'] for s in assessed)
    return {
        'active': active,
        'configuration_pending': bool(active and active['job']['version'] != job.get('version', 1)),
        'assessed': len(assessed), 'qualified': qualifying, 'shortlisted': shortlisted,
        'non_shortlisted': len(assessed) - shortlisted, 'capacity_excluded': qualifying - shortlisted,
        'review': sum(s['job_id'] == job['id'] and s.get('batch_id') and s.get('route') == 'review' for s in screenings),
        'remaining': max(0, active['job']['shortlist_capacity'] - shortlisted) if active and active['enforced'] else None,
    }


def active_allocation(job_id, state):
    active = state['job_allocations'].get(job_id)
    if active:
        return active
    # Pre-capacity runs retain their original threshold-only routing until reassessment.
    legacy = next((run for run in reversed(list(state['model_runs'].values()))
                   if run['job']['id'] == job_id and run.get('summary')), None)
    if legacy:
        return {'run_id': legacy['id'], 'job': {**legacy['job'], **capacity_config(legacy['job'])},
                'timestamp': legacy['finished_at'], 'enforced': False}
