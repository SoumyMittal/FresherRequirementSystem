from .config import MAXIMA


def make_features(record):
    """Exact historical feature definitions; constants never depend on the input batch."""
    r = dict(record)
    r['CGPA_Score'] = float(r['CGPA']) / 10
    r['CGPA_Eligible'] = int(float(r['CGPA']) >= float(r['Minimum CGPA']))
    r['CGPA_Gap'] = float(r['CGPA']) - float(r['Minimum CGPA'])
    r['Degree_Match'] = int(r['Degree'] in str(r['Preferred Degree']).split(', '))
    required = set(str(r['Required Skills']).split(', '))
    r['Skill_Match'] = round(len(set(str(r['Skills']).split(', ')) & required) / len(required), 2)
    r['Backlog_Score'] = 1 - float(r['Backlogs']) / 6
    for name in ('Project', 'Internship', 'Certification', 'Achievement'):
        count = float(r['Number of ' + name + 's'])
        r[name + '_Count'] = count
        r[name + '_Score'] = count / MAXIMA[name + '_Count']
    return r
