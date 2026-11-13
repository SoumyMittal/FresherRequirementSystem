from collections import Counter
import math

from .schema import NUMERIC_BOUNDS, RAW_COLUMNS


def missing(value):
    return value is None or str(value).strip().casefold() in ('', 'nan', 'null', 'na', 'n/a')


def parse_list(value):
    if missing(value) or str(value).strip().casefold() in ('none', 'n, o, n, e'):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(',') if part.strip()]


def normalize_number(field, value):
    lower, upper, integer = NUMERIC_BOUNDS[field]
    if isinstance(value, bool):
        raise ValueError('Enter a number.')
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError('Enter a number.') from None
    if not math.isfinite(number) or number < lower or (upper is not None and number > upper):
        raise ValueError(f'Use a value between {lower} and {upper}.' if upper is not None else f'Use a value of at least {lower}.')
    if integer and not number.is_integer():
        raise ValueError('Enter a whole number.')
    return int(number) if integer else number


def validate_records(records):
    ids = Counter(str(r.get('Application ID', '')).strip() for r in records)
    valid, invalid = [], []
    for index, record in enumerate(records):
        cleaned = dict(record)
        reasons = []
        for key in RAW_COLUMNS:
            value = record.get(key)
            optional_empty = key in ('Projects', 'Internships', 'Certifications', 'Achievements')
            count_key = 'Number of ' + key
            if missing(value) and not (optional_empty and str(record.get(count_key, '')).strip() in ('0', '0.0')):
                reasons.append(f'{key}: missing; needs review')
        app_id = str(record.get('Application ID', '')).strip()
        if app_id and ids[app_id] > 1:
            reasons.append('Application ID: duplicated in input')
        for key in NUMERIC_BOUNDS:
            value = record.get(key)
            if missing(value):
                continue
            try:
                cleaned[key] = normalize_number(key, value)
            except ValueError:
                reasons.append(f'{key}: invalid numeric value')
        for key in ('Skills', 'Required Skills', 'Preferred Degree'):
            if not parse_list(record.get(key)):
                reasons.append(f'{key}: must contain at least one entry')
        if reasons:
            invalid.append({'Source_Row': record.get('Source_Row', index + 2), 'Application ID': app_id,
                            'Candidate ID': record.get('Candidate ID', ''), 'Job ID': record.get('Job ID', ''),
                            'Errors': '; '.join(reasons)})
        else:
            valid.append(cleaned)
    return valid, invalid
