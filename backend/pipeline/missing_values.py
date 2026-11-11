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
