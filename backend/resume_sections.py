"""Canonical resume entry extraction, semantic section routing, and evidence-preserving grouping.

Descriptions, dates, employers, tools, stacks, and links are child details of entries
and never become standalone records or inflate counts.
"""
from __future__ import annotations

import re
from typing import Literal, Optional


class ResumeEntry:
    def __init__(
        self,
        category: Literal["project", "internship", "employment", "certification", "achievement"],
        title: str,
        organization: Optional[str] = None,
        date_text: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        description: Optional[str] = None,
        technologies: Optional[list[str]] = None,
        links: Optional[list[str]] = None,
        source_text: str = "",
        source_lines: Optional[list[int]] = None,
        page_numbers: Optional[list[int]] = None,
        confidence: Optional[float] = None,
        subtype: Optional[str] = None,
        section: Optional[str] = None,
    ):
        self.category = category
        self.title = (title or "").strip()
        self.organization = organization.strip() if organization else None
        self.date_text = date_text.strip() if date_text else None
        self.start_date = start_date.strip() if start_date else None
        self.end_date = end_date.strip() if end_date else None
        self.description = (description or "").strip()
        self.technologies = [t.strip() for t in (technologies or []) if t and str(t).strip()]
        self.links = [l.strip() for l in (links or []) if l and str(l).strip()]
        self.source_text = source_text or ""
        self.source_lines = list(source_lines or [])
        self.page_numbers = list(page_numbers or [])
        self.confidence = confidence
        self.subtype = subtype
        self.section = section

    def to_dict(self) -> dict:
        return {
            'category': self.category,
            'title': self.title,
            'organization': self.organization,
            'date_text': self.date_text,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'description': self.description,
            'technologies': list(self.technologies),
            'links': list(self.links),
            'source_text': self.source_text,
            'source_lines': list(self.source_lines),
            'source_line': self.source_lines[0] if self.source_lines else None,
            'page_numbers': list(self.page_numbers),
            'confidence': self.confidence,
            'subtype': self.subtype,
            'section': self.section,
        }

    def copy(self) -> ResumeEntry:
        return ResumeEntry(
            category=self.category,
            title=self.title,
            organization=self.organization,
            date_text=self.date_text,
            start_date=self.start_date,
            end_date=self.end_date,
            description=self.description,
            technologies=list(self.technologies),
            links=list(self.links),
            source_text=self.source_text,
            source_lines=list(self.source_lines),
            page_numbers=list(self.page_numbers),
            confidence=self.confidence,
            subtype=self.subtype,
            section=self.section,
        )


HEADINGS = {
    # Projects
    'project': 'Projects',
    'projects': 'Projects',
    'academic project': 'Projects',
    'academic projects': 'Projects',
    'personal project': 'Projects',
    'personal projects': 'Projects',
    'technical project': 'Projects',
    'technical projects': 'Projects',
    'selected project': 'Projects',
    'selected projects': 'Projects',
    'major project': 'Projects',
    'major projects': 'Projects',
    'engineering project': 'Projects',
    'engineering projects': 'Projects',
    'software project': 'Projects',
    'software projects': 'Projects',
    'key project': 'Projects',
    'key projects': 'Projects',
    'project name': 'Projects',
    'project title': 'Projects',
    'project experience': 'Projects',
    'research projects': 'Projects',

    # Internships
    'internship': 'Internships',
    'internships': 'Internships',
    'internship experience': 'Internships',
    'industrial training': 'Internships',
    'internship and training': 'Internships',
    'internships and training': 'Internships',

    # Experience
    'experience': 'Work Experience',
    'work experience': 'Work Experience',
    'professional experience': 'Work Experience',
    'work and experience': 'Work Experience',
    'employment': 'Work Experience',
    'employment history': 'Work Experience',
    'relevant experience': 'Work Experience',
    'relevant work experience': 'Work Experience',
    'training experience': 'Work Experience',
    'training and experience': 'Work Experience',
    'internships and experience': 'Work Experience',
    'experience and internships': 'Work Experience',
    'work history': 'Work Experience',
    'career history': 'Work Experience',
    'research experience': 'Work Experience',

    # Achievements
    'achievement': 'Achievements',
    'achievements': 'Achievements',
    'award': 'Achievements',
    'awards': 'Achievements',
    'awards and achievements': 'Achievements',
    'honors and awards': 'Achievements',
    'honours and awards': 'Achievements',
    'honors': 'Achievements',
    'honours': 'Achievements',
    'accomplishments': 'Achievements',
    'accomplishment': 'Achievements',
    'recognitions': 'Achievements',
    'recognition': 'Achievements',
    'scholarships': 'Achievements',
    'scholarship': 'Achievements',
    'patents': 'Achievements',
    'patent': 'Achievements',

    # Publications -> Category precedence rule routes these directly to Achievements
    'publication': 'Achievements',
    'publications': 'Achievements',
    'research publications': 'Achievements',
    'research publication': 'Achievements',
    'research papers': 'Achievements',
    'research paper': 'Achievements',
    'papers': 'Achievements',
    'conference papers': 'Achievements',
    'conference paper': 'Achievements',
    'journal publications': 'Achievements',
    'journal publication': 'Achievements',
    'journal papers': 'Achievements',
    'journal paper': 'Achievements',
    'awards and publications': 'Achievements',
    'publications and awards': 'Achievements',
    'selected publications': 'Achievements',

    # Certifications
    'certification': 'Certifications',
    'certifications': 'Certifications',
    'certificate': 'Certifications',
    'certificates': 'Certifications',
    'licenses': 'Certifications',
    'licenses and certifications': 'Certifications',
    'licenses and certificates': 'Certifications',
    'courses and certifications': 'Certifications',
    'certifications and courses': 'Certifications',
    'professional certifications': 'Certifications',
    'professional certificates': 'Certifications',
    'training and certifications': 'Certifications',

    # Mixed sections
    'projects and publications': 'Projects & Publications',
    'projects and research': 'Projects & Publications',
}

# Publications is removed from STOPS because it is routed to Achievements
STOPS = {
    'education', 'academic qualifications', 'academics', 'academic background',
    'skills', 'technical skills', 'key skills', 'core competencies',
    'summary', 'professional summary', 'executive summary', 'objective', 'career objective',
    'contact', 'contact info', 'contact details', 'interests', 'languages', 'references',
    'extracurricular activities', 'extracurriculars', 'hobbies', 'personal details',
    'profile', 'coursework', 'relevant coursework', 'declaration',
}

MONTHS = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
YEAR = r'(?:19|20)\d{2}'
DATE_ATOM = rf'(?:{MONTHS}\s+{YEAR}|\b{YEAR}\b|\b\d{{1,2}}/{YEAR}\b|\b\d{{1,2}}/\d{{1,2}}/{YEAR}\b)'
DATE_END_ATOM = rf'(?:{DATE_ATOM}|present|current|ongoing)'
DATE_RANGE_STR = rf'(?:{DATE_ATOM}(?:\s*(?:[-–—/]|to)\s*{DATE_END_ATOM})?)'

STANDALONE_DATE = re.compile(rf'^\s*(?:\(?\s*)?{DATE_RANGE_STR}\s*(?:\)?\s*)?$', re.I)
TRAILING_DATE = re.compile(rf'^(.*?)(?:\s{{2,}}|\t|\s+[-–—|]\s+|\s*\(\s*)\s*({DATE_RANGE_STR})\s*(?:\))?\s*$', re.I)

INTERN_ROLE_REGEX = re.compile(
    r'\b(?:intern(?:ship)?|trainee|apprentice|fellow(?:ship)?|summer\s+(?:intern|analyst|associate)|'
    r'winter\s+intern|student\s+intern|project\s+intern)\b',
    re.I
)

PUBLICATION_REGEX = re.compile(
    r'\b(?:publication|research paper|conference paper|journal paper|ieee|proceedings\b|springer|'
    r'accepted (?:at|by|in)|presented at|published in|doi:|arxiv|acm\b|scopus)\b',
    re.I
)

DESCRIPTION_VERBS = {
    'built', 'developed', 'designed', 'implemented', 'created', 'worked', 'working',
    'assisted', 'analyzed', 'analysed', 'used', 'using', 'utilized', 'integrated',
    'deployed', 'automated', 'achieved', 'improved', 'performed', 'managed',
    'collaborated', 'contributed', 'responsible', 'led', 'learned', 'tested',
    'maintained', 'optimized', 'enabled', 'completed', 'recognized', 'evaluated',
    'orchestrated', 'conducted', 'researched', 'published', 'presented', 'engineered',
    'programmed', 'spearheaded', 'authored', 'formulated', 'executed', 'trained',
    'fine-tuned', 'delivered', 'solved', 'established', 'supervised', 'streamlined',
    'supported', 'participated', 'gathered', 'extracted', 'cleaned', 'explored',
    'modeled', 'modelled', 'validated', 'visualized', 'visualised', 'received',
    'awarded', 'honored', 'honoured', 'won', 'authored', 'co-authored', 'investigated',
    'identified', 'generated', 'collected', 'processed', 'prepared', 'scaled'
}

DESCRIPTION_STARTERS = re.compile(
    r'^(?:'
    r'this|the project|the application|the model|the system|a web|a machine learning|an application|'
    r'technologies|tech stack|tools|description|duration|responsibilities|key responsibilities|'
    r'key achievements|details|metrics|achieving|focused on|maintaining|responsible for|'
    r'worked on|hands-on|duties include|duties included|in this role|during this internship'
    r')\b',
    re.I
)

KNOWN_TECHS = {
    'python', 'sql', 'scikit-learn', 'scikit learn', 'sklearn', 'pandas', 'numpy', 'scipy',
    'pytorch', 'tensorflow', 'keras', 'xgboost', 'lightgbm', 'catboost', 'streamlit',
    'flask', 'fastapi', 'django', 'docker', 'kubernetes', 'aws', 'gcp', 'azure', 'git',
    'linux', 'c++', 'c#', 'java', 'javascript', 'typescript', 'react', 'node',
    'nodejs', 'html', 'css', 'tableau', 'power bi', 'spark', 'hadoop', 'opencv',
    'nlp', 'llm', 'bert', 'transformers', 'random forest', 'decision tree', 'cnn', 'rnn',
    'lstm', 'mongodb', 'postgresql', 'mysql', 'sqlite', 'redis', 'graphql', 'rest api',
    'apis', 'hr analytics', 'machine learning', 'deep learning', 'data science', 'ai',
    'computer vision', 'sumo', 'yolo'
}


def normalize_heading(line: str) -> str:
    cleaned = line.strip().casefold()
    cleaned = cleaned.replace('&', ' and ')
    cleaned = re.sub(r'[^a-z0-9 ]', ' ', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()


def normalize_text_for_match(text: str) -> str:
    cleaned = re.sub(r'[^a-z0-9]', ' ', str(text or '').casefold())
    return re.sub(r'\s+', ' ', cleaned).strip()


def is_tech_stack_fragment(text: str) -> bool:
    if is_role_token(text):
        return False
    tokens = [t.strip().casefold() for t in re.split(r'[,|]', text) if t.strip()]
    if not tokens or len(tokens) < 2:
        return False
    match_count = sum(1 for t in tokens if t in KNOWN_TECHS or any(k in t for k in KNOWN_TECHS if len(k) >= 3))
    return match_count >= 2 and match_count >= len(tokens) / 2


def is_link_fragment(text: str) -> bool:
    return bool(re.search(r'\b(?:github|kaggle|gitlab|bitbucket|colab|doi\.org|http[s]?://)\b', text, re.I))


def is_org_token(text: str) -> bool:
    cleaned = text.strip()
    if re.search(r'\b(?:pvt|ltd|limited|technologies|solutions|inc|corp|company|labs|systems|consulting|studio|software|enterprises|agency|institute|foundation|organization|university|college|startup)\b', cleaned, re.I):
        return True
    if re.search(r'\b(?:\(virtual\)|\(remote\)|\(hybrid\)|\(on-site\)|\(part-time\)|\(full-time\)|virtual|remote|hybrid|on-site)\b', cleaned, re.I):
        return True
    return False


def is_role_token(text: str) -> bool:
    return bool(re.search(r'\b(?:intern(?:ship)?|trainee|engineer|developer|analyst|associate|consultant|manager|lead|specialist|fellow|scientist)\b', text, re.I))


def parse_project_line(line: str):
    cleaned = re.sub(r'^\s*(?:[•●▪◦*\-–—]+|\d+[.)])\s*', '', line).strip()
    cleaned = re.sub(r'^(?:project(?:\s*(?:name|title|\d+))?|title)\s*:\s*', '', cleaned, flags=re.I).strip()

    date_text = None
    date_match = TRAILING_DATE.match(cleaned)
    if date_match and not any(sep in date_match.group(2) for sep in [',', '|']):
        cleaned = date_match.group(1).strip()
        date_text = date_match.group(2).strip()

    parts = [p.strip() for p in re.split(r'\s+[|—]\s+', cleaned) if p.strip()]
    if len(parts) == 1:
        colon_split = re.split(r':\s+', cleaned, maxsplit=1)
        if len(colon_split) > 1 and len(colon_split[0].split()) <= 6:
            return colon_split[0].strip(), [], [], colon_split[1].strip(), date_text
        return cleaned, [], [], "", date_text

    title = parts[0]
    technologies = []
    links = []
    descriptions = []

    for part in parts[1:]:
        if is_link_fragment(part):
            links.append(part)
        elif STANDALONE_DATE.match(part):
            date_text = part
        elif is_tech_stack_fragment(part):
            for t in re.split(r'[,/|]', part):
                t_clean = t.strip()
                if t_clean and t_clean not in technologies:
                    technologies.append(t_clean)
        else:
            descriptions.append(part)

    desc_text = ' '.join(descriptions)
    return title, technologies, links, desc_text, date_text


def parse_experience_line(line: str):
    cleaned = re.sub(r'^\s*(?:[•●▪◦*\-–—]+|\d+[.)])\s*', '', line).strip()
    cleaned = re.sub(r'^(?:role|position|designation|title)\s*:\s*', '', cleaned, flags=re.I).strip()

    date_text = None
    date_match = TRAILING_DATE.match(cleaned)
    if date_match and not any(sep in date_match.group(2) for sep in [',', '|']):
        cleaned = date_match.group(1).strip()
        date_text = date_match.group(2).strip()

    parts = [p.strip() for p in re.split(r'\s+[|—]\s+|\s+-\s+', cleaned) if p.strip()]
    if len(parts) == 1:
        return parts[0], None, date_text

    role_cand = None
    org_cand = None
    for part in parts:
        if STANDALONE_DATE.match(part) and not date_text:
            date_text = part
        elif is_role_token(part) and not role_cand:
            role_cand = part
        elif is_org_token(part) and not org_cand:
            org_cand = part
        elif not role_cand:
            role_cand = part
        elif not org_cand:
            org_cand = part

    return role_cand or parts[0], org_cand, date_text


def is_description_line(title: str, raw_line: str, current_section: str, has_entries: bool) -> bool:
    if not has_entries:
        return False
    # In Achievements and Certifications, each bullet item is typically a distinct credential or award,
    # unless it is clearly an outcome/publication detail for the previous entry.
    if current_section in ('Achievements', 'Certifications'):
        if re.match(r'^(?:details|description|date|status|presented|accepted|published)\s*:', title, re.I):
            return True
        if STANDALONE_DATE.match(title):
            return True
        # Check if line is a publication/award detail bullet
        if re.search(r'\b(?:research paper|accepted (?:at|in|by)|presented at|published in|conference paper|journal paper|ieee|springer)\b', title, re.I):
            return True
        return False

    # In Projects and Work Experience:
    # Explicit bullet lines are descriptions unless they have an explicit title prefix
    if re.match(r'^\s*(?:[•●▪◦*\-–—]+|\d+[.)])\s*', raw_line) and not re.match(r'^\s*(?:[•●▪◦*\-–—]+|\d+[.)])\s*(?:project|role|position|title)\s*:', raw_line, re.I):
        return True
    # Action verbs starting the sentence
    words = title.split()
    first_word = words[0].casefold() if words else ""
    first_word_clean = re.sub(r'[^a-z]', '', first_word)
    if first_word_clean in DESCRIPTION_VERBS:
        return True
    if DESCRIPTION_STARTERS.match(title):
        return True
    if STANDALONE_DATE.match(title):
        return True
    if current_section == 'Projects' and title[:1].islower():
        return True
    if current_section in ('Work Experience', 'Internships') and is_org_token(title) and not is_role_token(title):
        return True
    if re.search(r'\b(?:\d+%\s*(?:accuracy|growth|reduction|improvement|increase)|accuracy achieved|\d+\s*fps|r²|auc)\b', title, re.I) and not is_role_token(title):
        return True
    return False


def extract_canonical_entries(text: str) -> tuple[dict[str, list[str] | None], dict[str, list[ResumeEntry]]]:
    groups: dict[str, list[ResumeEntry]] = {
        'Projects': [],
        'Internships': [],
        'Work Experience': [],
        'Certifications': [],
        'Achievements': []
    }
    seen = set()
    empty = set()
    current_section = None
    section_subtype = None
    pending_org = None
    pending_date = None

    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.isdigit() or re.search(r'FICTIONAL TEST RESUME|Not a real applicant|Incepta prototype', line, re.I):
            continue

        heading_part, separator, inline = line.partition(':')
        heading_candidate = heading_part if separator else line
        norm_h = normalize_heading(heading_candidate)

        if norm_h in HEADINGS:
            mapped_section = HEADINGS[norm_h]
            if mapped_section == 'Projects & Publications':
                current_section = 'Projects & Publications'
                section_subtype = None
            else:
                current_section = mapped_section
                section_subtype = 'publication' if norm_h in {
                    'publication', 'publications', 'research publications', 'research publication',
                    'research papers', 'research paper', 'papers', 'conference papers', 'conference paper',
                    'journal publications', 'journal publication', 'journal papers', 'journal paper',
                    'awards and publications', 'publications and awards', 'selected publications'
                } else None
            seen.add(current_section)
            pending_org = None
            if not inline.strip():
                continue
            line = inline.strip()
        elif norm_h in STOPS:
            current_section = None
            section_subtype = None
            pending_org = None
            continue

        if not current_section:
            continue

        cleaned_line = re.sub(r'^\s*(?:[•●▪◦*\-–—]+|\d+[.)])\s*', '', line).strip()
        if re.fullmatch(r'(?:none|nil|not provided|n/a)(?:\s*[-–:]\s*explicitly declared by candidate)?', cleaned_line, re.I):
            if current_section in groups:
                empty.add(current_section)
            continue

        target_section = current_section
        if current_section == 'Projects & Publications':
            if PUBLICATION_REGEX.search(cleaned_line):
                target_section = 'Achievements'
                section_subtype = 'publication'
            else:
                target_section = 'Projects'
                section_subtype = None

        active_list = groups.get(target_section if target_section in groups else 'Work Experience')

        # Check if line is a detail (description, date, stack, bullet)
        is_detail = is_description_line(cleaned_line, raw, target_section, bool(active_list))

        # Check if date line
        if STANDALONE_DATE.match(cleaned_line):
            if active_list:
                if not active_list[-1].date_text:
                    active_list[-1].date_text = cleaned_line
                else:
                    active_list[-1].description += ('\n' if active_list[-1].description else '') + cleaned_line
                active_list[-1].source_text += '\n' + raw
                active_list[-1].source_lines.append(number)
            else:
                pending_date = cleaned_line
            continue

        # Check if company-only line in Experience
        if target_section in ('Work Experience', 'Internships'):
            if is_org_token(cleaned_line) and not is_role_token(cleaned_line):
                if active_list and not active_list[-1].organization:
                    active_list[-1].organization = cleaned_line
                    active_list[-1].source_text += '\n' + raw
                    active_list[-1].source_lines.append(number)
                else:
                    pending_org = cleaned_line
                continue
            # If an organization was recorded on the previous line but not attached, attach it
            if active_list and not active_list[-1].organization and pending_org:
                active_list[-1].organization = pending_org
                pending_org = None

        if is_detail:
            if active_list:
                active_list[-1].description += ('\n' if active_list[-1].description else '') + cleaned_line
                active_list[-1].source_text += '\n' + raw
                active_list[-1].source_lines.append(number)
            continue

        # Handle new entry extraction per section
        if target_section == 'Projects':
            p_title, p_tech, p_links, p_desc, p_date = parse_project_line(line)
            if not p_title:
                continue
            # Check publication precedence: if project entry is actually a publication citation
            if PUBLICATION_REGEX.search(p_title) and not p_tech and not any('git' in l.lower() for l in p_links):
                entry = ResumeEntry(
                    category='achievement',
                    title=p_title,
                    date_text=p_date,
                    description=p_desc,
                    technologies=p_tech,
                    links=p_links,
                    source_text=raw,
                    source_lines=[number],
                    subtype='publication',
                    section='Achievements'
                )
                groups['Achievements'].append(entry)
                continue

            entry = ResumeEntry(
                category='project',
                title=p_title,
                date_text=p_date,
                description=p_desc,
                technologies=p_tech,
                links=p_links,
                source_text=raw,
                source_lines=[number],
                section='Projects'
            )
            # Avoid immediate duplicate consecutive titles with exact same date
            if active_list and active_list[-1].title.casefold() == p_title.casefold() and active_list[-1].date_text == p_date:
                continue
            active_list.append(entry)

        elif target_section in ('Work Experience', 'Internships'):
            role_title, org_name, date_val = parse_experience_line(line)
            if not role_title:
                continue

            # Links or pure tech stacks are never experience entries
            if is_link_fragment(role_title) or re.search(r'https?://', role_title, re.I):
                if active_list:
                    active_list[-1].links.append(role_title)
                    active_list[-1].source_text += '\n' + raw
                    active_list[-1].source_lines.append(number)
                continue

            if is_tech_stack_fragment(role_title):
                if active_list:
                    for t in re.split(r'[,/|]', role_title):
                        t_clean = t.strip()
                        if t_clean and t_clean not in active_list[-1].technologies:
                            active_list[-1].technologies.append(t_clean)
                    active_list[-1].source_text += '\n' + raw
                    active_list[-1].source_lines.append(number)
                continue

            # If the previous entry in this section was actually a company name preceding the role,
            # pop it and use it as the organization for this role.
            final_org = org_name or pending_org
            pending_org = None
            final_date = date_val or pending_date
            pending_date = None
            if active_list and is_role_token(role_title) and not is_role_token(active_list[-1].title):
                prev_non_role = active_list.pop()
                if not final_org:
                    final_org = prev_non_role.title
                if not final_date and prev_non_role.date_text:
                    final_date = prev_non_role.date_text

            is_intern = bool(INTERN_ROLE_REGEX.search(role_title))
            cat = 'internship' if (is_intern or target_section == 'Internships') else 'employment'
            entry = ResumeEntry(
                category=cat,
                title=role_title,
                organization=final_org,
                date_text=final_date,
                source_text=raw,
                source_lines=[number],
                section='Work Experience' if target_section == 'Work Experience' else 'Internships'
            )
            # Separate roles with different date ranges stay separate
            if active_list and active_list[-1].title.casefold() == role_title.casefold() and active_list[-1].date_text == date_val and active_list[-1].organization == final_org:
                continue
            active_list.append(entry)

        elif target_section == 'Achievements':
            ach_title = re.sub(r'^(?:award|achievement|title|paper|publication)\s*:\s*', '', cleaned_line, flags=re.I).strip()
            # Split off date if at trailing end
            date_val = None
            date_m = TRAILING_DATE.match(ach_title)
            if date_m:
                ach_title = date_m.group(1).strip()
                date_val = date_m.group(2).strip()
            split_desc = re.split(r'\s+[-–|]\s+|:\s+', ach_title, maxsplit=1)
            primary_title = split_desc[0].strip()
            extra_desc = split_desc[1].strip() if len(split_desc) > 1 else ""
            if not primary_title:
                continue
            entry = ResumeEntry(
                category='achievement',
                title=primary_title,
                date_text=date_val,
                description=extra_desc,
                source_text=raw,
                source_lines=[number],
                subtype=section_subtype or ('publication' if PUBLICATION_REGEX.search(primary_title) else None),
                section='Achievements'
            )
            if active_list and active_list[-1].title.casefold() == primary_title.casefold():
                continue
            active_list.append(entry)

        elif target_section == 'Certifications':
            cert_title = re.sub(r'^(?:certification|certificate|title|course)\s*:\s*', '', cleaned_line, flags=re.I).strip()
            date_val = None
            date_m = TRAILING_DATE.match(cert_title)
            if date_m:
                cert_title = date_m.group(1).strip()
                date_val = date_m.group(2).strip()
            split_desc = re.split(r'\s+[-–|]\s+|:\s+', cert_title, maxsplit=1)
            primary_title = split_desc[0].strip()
            extra_desc = split_desc[1].strip() if len(split_desc) > 1 else ""
            if not primary_title:
                continue
            entry = ResumeEntry(
                category='certification',
                title=primary_title,
                date_text=date_val,
                description=extra_desc,
                source_text=raw,
                source_lines=[number],
                section='Certifications'
            )
            if active_list and active_list[-1].title.casefold() == primary_title.casefold():
                continue
            active_list.append(entry)

    # Classify Work Experience into Internships vs Employment
    for entry in groups['Work Experience']:
        is_intern = bool(INTERN_ROLE_REGEX.search(entry.title))
        if not is_intern and entry.description and re.search(r'\b(?:completed\s+(?:a\s+)?(?:project-based\s+)?internship|throughout\s+the\s+internship|intern\b)\b', entry.description, re.I):
            # Only classify as intern if not a confirmed regular software engineer title
            if not re.search(r'\b(?:software engineer|senior|lead|director)\b', entry.title, re.I):
                is_intern = True

        if is_intern:
            # Check if an identical role with identical date range is already in Internships
            if not any(e.title.casefold() == entry.title.casefold() and e.date_text == entry.date_text for e in groups['Internships']):
                intern_copy = entry.copy()
                intern_copy.category = 'internship'
                intern_copy.section = 'Internships'
                groups['Internships'].append(intern_copy)
                seen.add('Internships')

    values = {}
    for key, entries in groups.items():
        if entries:
            values[key] = [e.title for e in entries]
        elif key in empty:
            values[key] = []
        else:
            values[key] = None

    return values, groups


def extract_sections(text: str) -> tuple[dict[str, list[str] | None], dict[str, list[dict]]]:
    values, canonical_groups = extract_canonical_entries(text)
    dict_groups = {
        key: [e.to_dict() for e in entries] if entries is not None else []
        for key, entries in canonical_groups.items()
    }
    return values, dict_groups


def reconcile_and_deduplicate(
    local_groups: dict[str, list[ResumeEntry] | list[dict]],
    gemini_groups: Optional[dict[str, list[ResumeEntry] | list[dict]]] = None,
    resume_text: str = ""
) -> tuple[dict[str, list[str] | None], dict[str, list[dict]]]:
    def to_canonical_list(items, default_category, default_section) -> list[ResumeEntry]:
        if not items:
            return []
        res = []
        for item in items:
            if isinstance(item, ResumeEntry):
                res.append(item.copy())
            elif isinstance(item, dict):
                res.append(ResumeEntry(
                    category=item.get('category', default_category),
                    title=item.get('title', ''),
                    organization=item.get('organization'),
                    date_text=item.get('date_text'),
                    start_date=item.get('start_date'),
                    end_date=item.get('end_date'),
                    description=item.get('description'),
                    technologies=item.get('technologies'),
                    links=item.get('links'),
                    source_text=item.get('source_text', ''),
                    source_lines=item.get('source_lines') or ([item['source_line']] if item.get('source_line') else []),
                    page_numbers=item.get('page_numbers'),
                    confidence=item.get('confidence'),
                    subtype=item.get('subtype'),
                    section=item.get('section', default_section)
                ))
        return res

    merged_by_cat: dict[str, list[ResumeEntry]] = {
        'project': [],
        'internship': [],
        'employment': [],
        'certification': [],
        'achievement': []
    }

    # Ingest local entries
    for sec_name, cat in [('Projects', 'project'), ('Internships', 'internship'),
                          ('Work Experience', 'employment'), ('Certifications', 'certification'),
                          ('Achievements', 'achievement')]:
        raw_items = local_groups.get(sec_name) if local_groups else []
        for e in to_canonical_list(raw_items, cat, sec_name):
            # Check publication precedence
            if sec_name == 'Projects' and PUBLICATION_REGEX.search(e.title + ' ' + (e.description or '')):
                e.category = 'achievement'
                e.subtype = 'publication'
                e.section = 'Achievements'
                merged_by_cat['achievement'].append(e)
            else:
                merged_by_cat[cat].append(e)

    # Ingest Gemini entries if provided
    if gemini_groups:
        for sec_name, cat in [('Projects', 'project'), ('Internships', 'internship'),
                              ('Work Experience', 'employment'), ('Certifications', 'certification'),
                              ('Achievements', 'achievement')]:
            raw_items = gemini_groups.get(sec_name) or gemini_groups.get(sec_name.lower()) or []
            for g_entry in to_canonical_list(raw_items, cat, sec_name):
                # Verify publication precedence
                if (sec_name in ('Projects', 'projects') or cat == 'project') and PUBLICATION_REGEX.search(g_entry.title + ' ' + (g_entry.description or '')):
                    g_entry.category = 'achievement'
                    g_entry.subtype = 'publication'
                    g_entry.section = 'Achievements'
                    cat = 'achievement'

                # Match against existing entries in this category
                existing_list = merged_by_cat[cat]
                matched = None
                norm_g_title = normalize_text_for_match(g_entry.title)

                for existing in existing_list:
                    norm_e_title = normalize_text_for_match(existing.title)
                    if not norm_g_title or not norm_e_title:
                        continue
                    # Check exact or near title match
                    if norm_g_title == norm_e_title or norm_g_title in norm_e_title or norm_e_title in norm_g_title:
                        # If both have explicit different dates, they are separate entries!
                        if existing.date_text and g_entry.date_text and normalize_text_for_match(existing.date_text) != normalize_text_for_match(g_entry.date_text):
                            continue
                        matched = existing
                        break

                if matched:
                    # Merge complementary details without duplication
                    if not matched.organization and g_entry.organization:
                        matched.organization = g_entry.organization
                    if not matched.date_text and g_entry.date_text:
                        matched.date_text = g_entry.date_text
                    for tech in g_entry.technologies:
                        if tech not in matched.technologies:
                            matched.technologies.append(tech)
                    for link in g_entry.links:
                        if link not in matched.links:
                            matched.links.append(link)
                    if g_entry.description and g_entry.description not in matched.description:
                        matched.description = (matched.description + '\n' + g_entry.description).strip()
                    for line_no in g_entry.source_lines:
                        if line_no not in matched.source_lines:
                            matched.source_lines.append(line_no)
                    if g_entry.source_text and g_entry.source_text not in matched.source_text:
                        matched.source_text = (matched.source_text + '\n' + g_entry.source_text).strip()
                else:
                    existing_list.append(g_entry)

    # Perform internal deduplication within each category
    for cat in merged_by_cat:
        deduped = []
        for entry in merged_by_cat[cat]:
            norm_title = normalize_text_for_match(entry.title)
            is_dup = False
            for prev in deduped:
                norm_prev = normalize_text_for_match(prev.title)
                if norm_title == norm_prev:
                    # If different dates exist, keep both!
                    if entry.date_text and prev.date_text and normalize_text_for_match(entry.date_text) != normalize_text_for_match(prev.date_text):
                        continue
                    # Otherwise merge details
                    is_dup = True
                    if not prev.organization and entry.organization:
                        prev.organization = entry.organization
                    if not prev.date_text and entry.date_text:
                        prev.date_text = entry.date_text
                    for tech in entry.technologies:
                        if tech not in prev.technologies:
                            prev.technologies.append(tech)
                    for link in entry.links:
                        if link not in prev.links:
                            prev.links.append(link)
                    if entry.description and entry.description not in prev.description:
                        prev.description = (prev.description + '\n' + entry.description).strip()
                    break
            if not is_dup:
                deduped.append(entry)
        merged_by_cat[cat] = deduped

    # Reassemble final sections
    final_dict_groups: dict[str, list[dict]] = {
        'Projects': [e.to_dict() for e in merged_by_cat['project']],
        'Internships': [e.to_dict() for e in merged_by_cat['internship']],
        'Work Experience': [e.to_dict() for e in (merged_by_cat['internship'] + merged_by_cat['employment'])],
        'Certifications': [e.to_dict() for e in merged_by_cat['certification']],
        'Achievements': [e.to_dict() for e in merged_by_cat['achievement']]
    }

    final_values: dict[str, list[str] | None] = {}
    for sec_name in ('Projects', 'Internships', 'Work Experience', 'Certifications', 'Achievements'):
        entries = final_dict_groups[sec_name]
        # Check if local was explicitly declared empty or missing
        was_empty = local_groups.get(sec_name) == [] and not gemini_groups
        was_none = local_groups.get(sec_name) is None and (not gemini_groups or gemini_groups.get(sec_name) is None)
        if entries:
            final_values[sec_name] = [e['title'] for e in entries]
        elif was_empty:
            final_values[sec_name] = []
        elif was_none:
            final_values[sec_name] = None
        else:
            final_values[sec_name] = []

    return final_values, final_dict_groups


def derive_counts(values: dict[str, list[str] | None]) -> dict[str, int | None]:
    counts = {}
    for sec in ('Projects', 'Internships', 'Certifications', 'Achievements'):
        val = values.get(sec)
        counts['Number of ' + sec] = len(val) if val is not None else None
    return counts
