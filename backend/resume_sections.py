"""Section-based, evidence-preserving grouping; descriptions never become counts."""
import re

HEADINGS = {
    'project':'Projects', 'projects':'Projects', 'academic projects':'Projects', 'personal projects':'Projects',
    'technical projects':'Projects', 'selected projects':'Projects', 'major projects':'Projects',
    'project name':'Projects', 'project title':'Projects', 'project experience':'Projects',
    'internship':'Internships', 'internships':'Internships', 'internship experience':'Internships',
    'industrial training':'Internships', 'internship and training':'Internships',
    'experience':'Work Experience', 'work experience':'Work Experience', 'professional experience':'Work Experience',
    'internships and experience':'Work Experience', 'experience and internships':'Work Experience',
    'achievement':'Achievements', 'achievements':'Achievements', 'awards':'Achievements',
    'awards and achievements':'Achievements', 'honors and awards':'Achievements',
    'certification':'Certifications', 'certifications':'Certifications', 'certificates':'Certifications',
    'certifications and courses':'Certifications',
}
STOPS = {'education','academic qualifications','academic background','skills','technical skills','summary',
         'professional summary','objective','career objective','contact','interests','languages','references',
         'extracurricular activities','hobbies','publications','personal details','profile','coursework'}
DESCRIPTION = re.compile(r'^(?:built|developed|designed|implemented|created|worked|working|assisted|analyzed|analysed|'
                         r'used|using|utilized|integrated|deployed|automated|achieved|improved|performed|managed|'
                         r'collaborated|contributed|responsible|led|learned|tested|maintained|optimized|enabled|'
                         r'this|the project|the application|a web|a machine learning|an application|technologies|tech stack|tools|description|'
                         r'duration|organization|company|location|link|github|role\s*:|https?://)\b', re.I)
DATE = re.compile(r'^(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+)?20\d{2}(?:\s*[-–|/].*)?$',re.I)


def normalize_heading(line):
    return re.sub(r'[^a-z0-9 ]',' ',line.casefold().replace('&',' and ')).strip()


def extract_sections(text):
    groups={key:[] for key in ['Projects','Internships','Work Experience','Certifications','Achievements']}
    seen=set()
    empty=set()
    current=None
    for number, raw in enumerate(text.splitlines(),1):
        line=raw.strip()
        if not line or line.isdigit() or re.search(r'FICTIONAL TEST RESUME|Not a real applicant|Incepta prototype',line,re.I):
            continue
        heading_part, separator, inline=line.partition(':')
        heading=re.sub(r'\s+',' ',normalize_heading(heading_part if separator else line))
        if heading in HEADINGS:
            current=HEADINGS[heading];seen.add(current)
            if not inline.strip():continue
            line=inline.strip()
        elif heading in STOPS:
            current=None;continue
        if not current:continue
        title=re.sub(r'^\s*(?:[•●▪◦*\-–]+|\d+[.)])\s*','',line).strip()
        title=re.sub(r'^(?:project(?:\s*(?:name|title|\d+))?|title)\s*:\s*','',title,flags=re.I)
        if current in ('Internships','Work Experience'):
            title=re.sub(r'^(?:role|position|designation)\s*:\s*','',title,flags=re.I)
        if re.fullmatch(r'(?:none|nil|not provided|n/a)(?:\s*[-–:]\s*explicitly declared by candidate)?',title,re.I):
            empty.add(current);continue
        entries=groups[current]
        if current in ('Internships','Work Experience') and entries and re.search(r'\b(?:intern|trainee|engineer|developer|analyst)\b',title,re.I):
            previous=entries[-1]
            if not re.search(r'\b(?:intern|trainee|engineer|developer|analyst)\b',previous['title'],re.I) and re.search(r'\b(?:company|corp|ltd|inc|labs|technologies|solutions)\b',previous['title'],re.I):
                previous['description']=previous['title']+'\n'+previous['description']
                previous['title']=title
                previous['source_text']+='\n'+raw
                continue
        description=bool(DESCRIPTION.match(title) or DATE.match(title))
        if entries and current=='Projects' and title[:1].islower():description=True
        if current=='Achievements':
            description=bool(re.match(r'^(?:details|description|date)\s*:',title,re.I))
        # A company/date line after a named internship belongs to that role.
        if current in ('Internships','Work Experience') and entries and re.search(r'\b(?:intern|trainee|engineer|developer|analyst)\b',entries[-1]['title'],re.I):
            if re.search(r'\b(?:pvt|ltd|limited|technologies|solutions|inc|corp|company|labs|systems|consulting)\b',title,re.I) and not re.search(r'\b(?:intern|trainee|engineer|developer|analyst)\b',title,re.I):
                description=True
        if description:
            if entries:
                entries[-1]['description']+='\n'+title
                entries[-1]['source_text']+='\n'+raw
            continue
        # A title followed by a colon and description is one entry.
        split=re.split(r'\s+(?:[-–|])\s+|:\s+',title,maxsplit=1)
        entry_title=split[0].strip()
        if not entry_title:continue
        entry={'title':entry_title,'description':split[1] if len(split)>1 else '',
               'source_text':raw,'source_line':number,'section':current}
        if entries and entry_title.casefold()==entries[-1]['title'].casefold():continue
        entries.append(entry)
    for entry in groups['Work Experience']:
        if re.search(r'\b(?:intern(?:ship)?|trainee)\b',entry['title'],re.I):
            if not any(e['title'].casefold()==entry['title'].casefold() for e in groups['Internships']):
                groups['Internships'].append(dict(entry))
                seen.add('Internships')
    values={key:[entry['title'] for entry in entries] if entries else [] if key in empty else None for key,entries in groups.items()}
    return values, groups
