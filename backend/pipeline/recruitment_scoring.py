WEIGHTS = {'Skill_Match': .35, 'CGPA_Score': .20, 'Project_Score': .15, 'Internship_Score': .10,
           'Certification_Score': .05, 'Achievement_Score': .05, 'Degree_Match': .05, 'Backlog_Score': .05}


def recruitment_score(features, legacy_penalties=False):
    score = round(sum(float(features[key]) * weight for key, weight in WEIGHTS.items()) * 100, 2)
    if legacy_penalties:
        if not features['CGPA_Eligible']:
            score *= .70
        if not features['Degree_Match']:
            score *= .80
    return round(score, 2)
