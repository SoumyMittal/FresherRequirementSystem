def rank_records(records):
    """Stable per-job ranks. Threshold segments remain independent of these ranks."""
    groups = {}
    for record in records:
        groups.setdefault(record['Job ID'], []).append(record)
    for group in groups.values():
        for score, rank in [('Model_Score', 'Model_Rank'), ('Recruitment_Score', 'Recruitment_Rank')]:
            ordered = sorted(group, key=lambda r: (-r[score], str(r['Application ID'])))
            for index, record in enumerate(ordered, 1):
                record[rank] = index
    return records
