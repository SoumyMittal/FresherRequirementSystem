def model_rank_key(record):
    return (-record['Model_Score'], -record['Recruitment_Score'], str(record['Application ID']))


def rank_records(records):
    """Stable per-job ranks. Threshold segments remain independent of these ranks."""
    groups = {}
    for record in records:
        groups.setdefault(record['Job ID'], []).append(record)
    for group in groups.values():
        for key, rank in [(model_rank_key, 'Model_Rank'),
                          (lambda r: (-r['Recruitment_Score'], str(r['Application ID'])), 'Recruitment_Rank')]:
            ordered = sorted(group, key=key)
            for index, record in enumerate(ordered, 1):
                record[rank] = index
    return records
