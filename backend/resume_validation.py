"""Source-backed validation for resume profiles and HR corrections."""
import re

from backend.pipeline.validation import missing, normalize_number
from backend.resume_sections import HEADINGS, normalize_heading

NUMERIC_FIELDS = ('CGPA', 'Class 10 Percentage', 'Class 12 Percentage', 'Backlogs')
LIST_FIELDS = ('Skills', 'Projects', 'Internships', 'Certifications', 'Achievements')
PROFILE_FIELDS = ('Full Name', 'Email', 'Degree', 'Specialization', *NUMERIC_FIELDS, *LIST_FIELDS)
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
DEGREES = {'btech': 'B.Tech', 'be': 'B.E', 'bsc': 'B.Sc', 'bca': 'BCA', 'mca': 'MCA',
           'mtech': 'M.Tech', 'msc': 'M.Sc', 'mba': 'MBA', 'bcom': 'B.Com', 'ba': 'B.A'}
DEGREE = r'\b(B\.?\s?Tech|B\.?\s?E|B\.?\s?Sc|BCA|MCA|M\.?\s?Tech|M\.?\s?Sc|MBA|B\.?\s?Com|B\.?\s?A)\b'
SPECIALIZATION_LABEL = re.compile(
    r'\b(?:speciali[sz](?:ing|ed)\s+in|speciali[sz]ations?\s*(?::|\bin\b)|'
    r'majoring\s+in|majors?\s*(?::|\bin\b)|concentration\s*(?::|\bin\b))\s*', re.I)
DEGREE_RE = re.compile(DEGREE, re.I)
KNOWN_DISCIPLINE = re.compile(
    r'\b(?:computer science|information technology|artificial intelligence|data science|electronics|'
    r'electrical|engineering|mathematics|computing|statistics|physics|chemistry|economics|'
    r'cyber\s*security|machine learning|business administration|commerce|AI|DS|CSE|ECE|EEE)\b', re.I)
EDUCATION_BOUNDARY = re.compile(
    r'\s{2,}|[.!?](?=\s|$)|[|()[\]]|\s+[-–—]\s+|'
    r'\s+\b(?:student|graduate|at|from|with|passionate|expected|graduation|semester|CGPA|GPA|'
    r'currently|pursuing|seeking|interested|university|college|institute)\b|\b(?:19|20)\d{2}\b', re.I)
SPECIALIZATION_ALIASES = {
    'ai': 'artificial intelligence', 'ds': 'data science', 'cse': 'computer science and engineering',
    'ece': 'electronics and communication engineering', 'eee': 'electrical and electronics engineering',
}
NUMERIC_LABELS = {
    'CGPA': r'\b(?:CGPA|GPA)\b',
    'Class 10 Percentage': r'\b(?:Class[ \t]*(?:10|X)|10th|SSLC?|matriculation)\b',
    'Class 12 Percentage': r'\b(?:Class[ \t]*(?:12|XII)|12th|HSC|higher secondary|senior secondary|intermediate)\b',
    'Backlogs': r'\b(?:active\s+)?backlogs?\b',
}
UNKNOWN = re.compile(r'^(?:not provided|not available|unknown|n/?a|[-–—])$', re.I)


def specialization_key(value):
    words = re.findall(r'\w+|&', (value or '').casefold())
    return ' '.join('and' if word == '&' else SPECIALIZATION_ALIASES.get(word, word) for word in words)


def specialization_facts(pages):
    """Read specialization names from education clauses and keep their source lines."""
    facts = {}
    for page, text in enumerate(pages, 1):
        lines = text.splitlines()
        for index, raw in enumerate(lines):
            line = raw.strip()
            for degree in DEGREE_RE.finditer(line):
                # B.Tech. is a degree abbreviation, so its final dot is not a sentence boundary.
                end = degree.end()
                line = line[:end] + ' ' + line[end + 1:] if line[end:end + 1] == '.' else line
            starts = [(match.end(), True) for match in SPECIALIZATION_LABEL.finditer(line)]
            for match in DEGREE_RE.finditer(line):
                suffix = line[match.end():].strip()
                prefix = re.match(r'^(?:in\b\s*|[:(–—-]\s*)', suffix, re.I)
                starts.append((len(line) - len(suffix) + (prefix.end() if prefix else 0), bool(prefix)))
            for start, explicit in starts:
                clause = line[start:]
                # A second degree or explicit label starts its own clause.
                boundary = min((match.start() for pattern in (DEGREE_RE, SPECIALIZATION_LABEL)
                                if (match := pattern.search(clause))), default=len(clause))
                clause = EDUCATION_BOUNDARY.split(clause[:boundary], maxsplit=1)[0].strip()
                quote = raw.strip()
                if index + 1 < len(lines) and (re.search(r'(?:\band|&)$', clause, re.I) or (not clause and explicit and not line[start:].strip())):
                    continuation = EDUCATION_BOUNDARY.split(lines[index + 1].strip(), maxsplit=1)[0]
                    if KNOWN_DISCIPLINE.search(continuation) and not DEGREE_RE.search(continuation):
                        clause = f'{clause} {continuation}'.strip()
                        quote += '\n' + lines[index + 1].strip()
                for name in re.split(r'[,;]', clause):
                    name = name.strip(' \t:-–—')
                    if not re.fullmatch(r"[^\W\d_][\w &/'’-]*", name) or UNKNOWN.fullmatch(name):
                        continue
                    if not KNOWN_DISCIPLINE.search(name) and (not explicit or name != clause):
                        continue
                    if re.match(r'^(?:student|graduate|candidate|degree|education|pursuing|my|the|a|an|progress|final year)\b', name, re.I):
                        continue
                    key = specialization_key(name)
                    source = {'page': page, 'text': quote}
                    if key not in facts:
                        facts[key] = (name, [])
                    if source not in facts[key][1]:
                        facts[key][1].append(source)
    return facts


def issue(field, value, reason, evidence=(), blocking=True, provenance='invalid'):
    return dict(field=field, value=value, reason=reason, evidence=list(evidence),
                blocking=blocking, provenance=provenance)


def evidence_for_pages(pages, snippets):
    matches = []
    for index, page in enumerate(pages, 1):
        lines = page.splitlines()
        for snippet in snippets:
            if not snippet:
                continue
            quote = next((line.strip() for line in lines if snippet.casefold() in line.casefold()), None)
            if quote:
                item = {'page': index, 'text': quote}
                if item not in matches:
                    matches.append(item)
    return matches


def academic_facts(pages):
    """Keep unsupported scales, contradictory facts and unreadable tokens visible."""
    facts, evidence, issues = {}, {}, []
    for field, label in NUMERIC_LABELS.items():
        observations = []
        for page, text in enumerate(pages, 1):
            for line in text.splitlines():
                match = re.search(label, line, re.I)
                if not match:
                    continue
                suffix = line[match.end():].strip()
                if 'Percentage' in field:
                    suffix = re.split(r'\b(?:Class\s*(?:10|12|XII|X)|10th|12th|CGPA|GPA|Backlogs?)\b',
                                      suffix, maxsplit=1, flags=re.I)[0]
                if field == 'Backlogs' and re.search(r'\bno\s+(?:active\s+)?backlogs?\b', line, re.I):
                    suffix = '0'
                suffix = re.sub(r'^(?:percentage|marks|score)\b', '', suffix, flags=re.I).strip()
                suffix = re.sub(r'^(?:[:=]\s*|[-–—]\s+)', '', suffix).strip()
                if UNKNOWN.fullmatch(suffix):
                    continue
                source = {'page': page, 'text': line.strip()}
                if field == 'Backlogs' and suffix.casefold() in ('none', 'nil'):
                    suffix = '0'
                number = re.match(r'[+-]?\d+(?:\.\d+)?', suffix)
                if 'Percentage' in field:
                    number = re.search(r'([+-]?\d+(?:\.\d+)?)\s*%', suffix)
                if not number:
                    if re.match(r'^(?:[:=]|(?:percentage|marks|score)\b)', line[match.end():].strip(), re.I) or suffix[:1].isdigit():
                        observations.append((suffix, source, 'The source does not state a readable value in the expected format.', 'unextractable'))
                    continue
                token = number.group(1) if 'Percentage' in field else number.group()
                value = float(token)
                reason = None
                if field == 'CGPA':
                    scale = re.match(r'\s*(?:/|out of)\s*(\d+(?:\.\d+)?)', suffix[number.end():], re.I)
                    if scale and float(scale.group(1)) != 10:
                        reason = 'The model requires a 10-point CGPA. Verify the original scale.'
                if suffix[number.end():].startswith(('.', ',')):
                    reason = 'The source uses an ambiguous number format.'
                observations.append((value, source, reason, 'ambiguous' if reason else 'observed'))
        if not observations:
            continue
        value = observations[0][0]
        facts[field] = value
        evidence[field] = [item[1] for item in observations]
        for extracted, source, reason, provenance in observations:
            if reason:
                issues.append(issue(field, extracted, reason, [source], provenance=provenance))
        if len({item[0] for item in observations}) > 1:
            issues.append(issue(field, value, 'The resume contains conflicting values.', evidence[field], provenance='ambiguous'))
    return facts, evidence, issues


def profile_sources(data, pages, grouped, gemini, extraction_issues):
    evidence = {}
    for field in ('Full Name', 'Email', 'Degree', 'Specialization', 'Skills'):
        values = data.get(field)
        snippets = values if isinstance(values, list) else [values]
        if field == 'Degree':
            snippets = [m.group() for page in pages for m in re.finditer(DEGREE, page, re.I)]
        evidence[field] = evidence_for_pages(pages, snippets)
    for section, entries in grouped.items():
        evidence[section] = []
        for entry in entries:
            sources = evidence_for_pages(pages, [entry['title'], *entry['source_text'].splitlines()])
            entry['page_numbers'] = sorted({source['page'] for source in sources})
            evidence[section].extend(source for source in sources if source not in evidence[section])
        if not entries and data.get(section) in (None, []):
            for page, text in enumerate(pages, 1):
                headings = [line.strip() for line in text.splitlines()
                            if HEADINGS.get(normalize_heading(line.partition(':')[0])) == section]
                if headings and section != 'Work Experience':
                    source = {'page': page, 'text': headings[0]}
                    evidence[section].append(source)
                    if data.get(section) is None:
                        extraction_issues.append(issue(section, None, 'A section is present but its entries could not be resolved.',
                                                       [source], provenance='unextractable'))
                    break
    for field, value in (gemini or {}).get('evidence', {}).items():
        if isinstance(value, str):
            evidence[field] = evidence_for_pages(pages, value.splitlines()) or evidence.get(field, [])
    return evidence


def validate_profile(data, evidence, extraction_issues=(), corrected=()):
    issues = [item for item in extraction_issues if item['field'] not in corrected]
    normalized = {}
    for field in PROFILE_FIELDS:
        value = data.get(field)
        if missing(value) or (isinstance(value, str) and UNKNOWN.fullmatch(value.strip())):
            normalized[field] = None
            continue
        try:
            if field in NUMERIC_FIELDS:
                value = normalize_number(field, value)
            elif field in LIST_FIELDS:
                if not isinstance(value, list) or any(not isinstance(entry, str) or not entry.strip() for entry in value):
                    raise ValueError('Enter a list with one item per line.')
                value = list(dict.fromkeys(entry.strip() for entry in value))
            elif not isinstance(value, str):
                raise ValueError('Enter a text value.')
            elif field == 'Email' and not EMAIL.fullmatch(value.strip()):
                raise ValueError('Enter an email address in a valid format.')
            else:
                value = value.strip()
        except ValueError as exc:
            issues.append(issue(field, value, str(exc), evidence.get(field, []), blocking=field not in ('Email', 'Full Name')))
        normalized[field] = value
    provenance = {}
    for field, value in normalized.items():
        finding = next((item for item in issues if item['field'] == field), None)
        status = ('explicit_empty' if value == [] else 'explicit_zero' if value == 0 else
                  'absent' if value is None else 'extracted')
        provenance[field] = {'status': finding['provenance'] if finding else status,
                             'origin': 'hr_correction' if field in corrected else 'resume'}
        if field in LIST_FIELDS and field != 'Skills':
            provenance['Number of ' + field] = dict(provenance[field])
    return normalized, issues, provenance


def explicit_skills(pages, vocabulary):
    """Preserve tools outside the model's known vocabulary when a skills list names them."""
    known = {item.casefold(): item for item in vocabulary}
    declared = []
    for page in pages:
        active = False
        for line in page.splitlines():
            head, separator, inline = line.strip().partition(':')
            heading = normalize_heading(head)
            if heading in ('skills', 'technical skills', 'core skills', 'key skills', 'tools and technologies'):
                active = not separator or not inline.strip()
                line = inline if separator else ''
                if inline.strip():
                    declared.extend(part.strip(' \t•-') for part in re.split(r'[,;|•]', line) if part.strip(' \t•-'))
                continue
            elif heading in HEADINGS or heading in ('education', 'summary', 'profile', 'interests', 'languages', 'contact'):
                active = False
            if active and line.strip():
                declared.extend(part.strip(' \t•-') for part in re.split(r'[,;|•]', line) if part.strip(' \t•-'))
    if not declared:
        return None
    if all(item.casefold() in ('none', 'nil') for item in declared):
        return []
    return list(dict.fromkeys(known.get(item.casefold(), item) for item in declared
                              if item.casefold() not in ('none', 'nil') and not UNKNOWN.fullmatch(item))) or None
