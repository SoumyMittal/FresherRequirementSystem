"""Optional recovery only from unambiguous, valid same-candidate profile values."""
from .schema import RAW_COLUMNS, NUMERIC_BOUNDS
from .validation import missing
import math

PROFILE_FIELDS = tuple(c for c in RAW_COLUMNS if c not in (
    'Application ID', 'Candidate ID', 'Job ID', 'Job Role', 'Number of Openings', 'Required Skills', 'Preferred Degree', 'Minimum CGPA'))


def recover_candidate_fields(records):
    result = [dict(r) for r in records]
    candidates = {}
    for row in records:
        candidate = str(row.get('Candidate ID', '')).strip()
        if not candidate:
            continue
        for field in PROFILE_FIELDS:
            value = row.get(field)
            if missing(value):
                continue
            if field in NUMERIC_BOUNDS:
                lo, hi, integer = NUMERIC_BOUNDS[field]
                try:
                    v = float(value)
                    if not math.isfinite(v) or v < lo or (hi is not None and v > hi) or (integer and not v.is_integer()):
                        continue
                    identity = str(v)
                except (ValueError, TypeError):
                    continue
            else:
                identity = str(value).strip()
            candidates.setdefault((candidate, field), {})[identity] = value
    for row in result:
        recovered = []
        for field in PROFILE_FIELDS:
            options = candidates.get((str(row.get('Candidate ID', '')).strip(), field), {})
            if missing(row.get(field)) and len(options) == 1:
                row[field] = next(iter(options.values()))
                recovered.append(field)
        row['Processing_Warnings'] = 'Recovered from same-candidate record: ' + ', '.join(recovered) if recovered else ''
    return result


def prepare_model_record(record, reference, fallbacks=None):
    """Notebook 03 fallbacks on a copy; never overwrite extracted evidence.

    Reference rows supply stable medians/modes rather than upload-batch statistics.
    """
    result = dict(record)
    if fallbacks is None:
        fallbacks = reference_fallbacks(reference, (field for field in PROFILE_FIELDS if missing(result.get(field))))
    filled = {field: info for field, info in fallbacks.items() if missing(result.get(field))}
    result.update({field: info['value'] for field, info in filled.items()})
    return result, filled


def reference_fallbacks(reference, fields=PROFILE_FIELDS):
    from statistics import median
    from collections import Counter

    filled = {}
    for field in fields:
        values = [row.get(field) for row in reference if not missing(row.get(field))]
        if field in NUMERIC_BOUNDS:
            lo, hi, integer = NUMERIC_BOUNDS[field]
            numbers = []
            for value in values:
                try:
                    number = float(value)
                    if math.isfinite(number) and number >= lo and (hi is None or number <= hi):
                        numbers.append(number)
                except (TypeError, ValueError):
                    pass
            if not numbers:
                continue
            value = median(numbers)
            # Counts must stay integral even when the median falls between integers.
            value = int(math.floor(value + .5)) if integer else value
            rule = 'reference median'
        elif field == 'Specialization' and values:
            value = Counter(str(v).strip() for v in values).most_common(1)[0][0]
            rule = 'reference mode'
        else:
            value = 'Not Provided'
            rule = 'missing text marker'
        filled[field] = {'value': value, 'method': rule}
    return filled
