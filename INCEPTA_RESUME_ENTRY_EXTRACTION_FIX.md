# Incepta — Resume Entry Extraction and Classification Correction Specification

**Repository:** `SoumyMittal/FresherRequirementSystem`  
**Scope:** Targeted correction to the existing working Incepta application  
**Priority:** High — resume parsing correctness  
**Instruction:** Read this document fully, inspect the existing repository, implement the changes, and run the tests. Do not rebuild unrelated parts of the product.

---

## 1. Purpose and scope

The current application is functional, and its existing workflows, UI, validation, CSV export, model pipeline and other completed work should be preserved.

This task addresses a focused set of parser defects:

1. A single internship is sometimes represented as multiple internships because role metadata, date lines and description text are incorrectly split into separate records.
2. A project's title, technology stack, link and description bullets can be extracted as separate projects.
3. Research work and publications must belong to **Achievements**, not **Projects**.
4. Internship roles must be found even when they are under `Experience`, `Work Experience`, `Professional Experience` or similar headings.
5. Entry counts must represent distinct real entries and must not be inflated by descriptions, dates, company names, technology lists, bullets or links.
6. The parser must preserve evidence and uncertainty rather than inventing entries to fill a count.

Do not change model semantics, feature schema, recruitment scoring, missing-value policy, branding, unrelated UI or previously completed behaviour unless strictly required to connect the corrected parser.

---

## 2. Repository findings to guide implementation

The current implementation includes:

- `backend/resume_sections.py` — rule-based section and entry grouping.
- `backend/gemini_parser.py` — Gemini structured extraction into separate lists.
- `backend/app.py` — PDF extraction, local/Gemini parser merge, count derivation and review API.
- `backend/pipeline/schema.py` — raw CSV field definitions.
- `backend/pipeline/feature_engineering.py` — model features.

Important current behaviour that must be reviewed and corrected:

### 2.1 Current local section grouping weakness

`resume_sections.py` loops through each text line and often treats any line that is not recognized as a description as a new entry. This can split a single experience into separate records when OCR order or formatting separates:
- role/title;
- date;
- employer;
- responsibility or outcome statements.

It also has incomplete category boundaries:
- `publications` currently stops parsing rather than routing publication entries into `Achievements`;
- research/publication headings are not consistently routed into the achievements collection;
- experience headings and internship role classification are handled through separate passes that can create inconsistent results.

### 2.2 Current Gemini extraction weakness

`gemini_parser.py` requests `projects`, `internships`, `certifications`, and `achievements` as independent lists. The instructions say descriptions are not entries, but the schema and prompt do not fully enforce a parent-entry/child-detail relationship.

The result is accepted and mapped as a simple list of titles. The parser should instead preserve structured entry records and use one shared post-processing/deduplication/category-reconciliation step for local and Gemini results.

### 2.3 Current count derivation

`app.py` currently derives counts with:

```python
for section in ('Projects','Internships','Certifications','Achievements'):
    data['Number of '+section] = len(data[section]) if data.get(section) is not None else None
```

This is valid only after entries have been deduplicated, classified and grouped correctly. Do not fix inflated counts with a numeric cap or by subtracting guessed duplicates. Fix the underlying entry collection first.

---

## 3. Canonical data model: one record per real-world entry

Refactor internal extraction to use a canonical entry object. Adapt exact class names to project conventions, but preserve these fields:

```python
class ResumeEntry:
    category: Literal[
        "project",
        "internship",
        "employment",
        "certification",
        "achievement",
    ]
    title: str
    organization: str | None
    date_text: str | None
    start_date: str | None
    end_date: str | None
    description: str | None
    technologies: list[str]
    links: list[str]
    source_text: str
    source_lines: list[int]
    page_numbers: list[int]
    confidence: float | None
```

Rules:

- One real project, role, publication, award or certificate = one `ResumeEntry`.
- Description bullets, date lines, employer names, tools, technologies and URLs are child details of the parent entry.
- Do not create entries from every line or bullet.
- `title` should be the role/project/publication/credential title, not the description.
- `organization` is optional and separate.
- Keep source evidence and provenance for every entry.
- Retain raw source text if parsing is ambiguous.
- Keep entries with uncertain details for human review, but do not inflate confirmed counts with low-confidence fragments.

Do not use a schema that loses the difference between a role, employer, date and responsibility statement.

---

## 4. Section detection and category precedence

Implement normalized, case-insensitive, punctuation-tolerant section heading matching. Support heading variants.

### 4.1 Projects

Route to `Projects`:
- Projects
- Academic Projects
- Personal Projects
- Technical Projects
- Selected Projects
- Major Projects
- Engineering Projects
- Software Projects
- Key Projects
- Research Projects **only when the content is clearly a project implementation**, not a publication/manuscript

### 4.2 Experience and internships

Recognize headings:
- Experience
- Work Experience
- Professional Experience
- Internship
- Internships
- Internship Experience
- Work & Experience
- Employment
- Relevant Experience
- Industrial Training
- Training Experience
- Research Experience

A section named `Experience` does not mean every line is an internship. Classify each role using title and evidence.

### 4.3 Achievements, research and publications

Route to `Achievements`:
- Achievements
- Achievement
- Awards
- Honors / Honours
- Accomplishments
- Publications
- Publication
- Research Publications
- Research Papers
- Papers
- Conference Papers
- Journal Publications
- Patent / Patents
- Scholarships
- Recognitions
- Awards & Achievements

**Category precedence rule:** If a section explicitly identifies publications/research papers/papers/conference papers/journal publications, entries in that section must be categorized as `Achievements` (with subtype metadata such as `publication` or `research_paper` if supported). They must not be copied into `Projects`.

Do not classify a publication as a project merely because its title mentions a technical subject, model, system or algorithm.

A research project describing implementation of a system can remain a project. A paper/manuscript/publication, conference paper, journal article, patent, award or research recognition belongs in Achievements.

If an item genuinely represents both a research project and a resulting publication:
- represent the implementation as a project only if the resume provides distinct project evidence;
- represent the publication as an achievement;
- link the two via an optional relationship/reference;
- do not duplicate identical text as two entries without distinct evidence.

### 4.4 Certifications

Recognize:
- Certifications
- Certificates
- Licenses
- Courses & Certifications
- Professional Certifications
- Training & Certifications

Course attendance or training is not automatically a certification unless the source indicates a certificate, credential, licence or completed course that the current product treats as a certification.

### 4.5 Heading precedence

Examples:
- `Research Publications` → Achievements
- `Research Projects` → Projects, unless entries are clearly paper/publication citations
- `Research Experience` → experience context; classify each role from evidence
- `Projects & Publications` → split items by their own type/evidence; publication records go to Achievements, implementation projects go to Projects

The parser must never route the entire `Publications` section into `Projects`.

---

## 5. Entry-boundary detection: grouping child lines correctly

Implement a two-stage approach:

1. Detect sections and collect ordered lines with source location.
2. Within each section, identify entry starts and attach subsequent detail lines to the active entry.

Use evidence such as:
- typographic/layout cues retained from PDF extraction where available;
- bullet numbering and indentation;
- dates;
- title-like wording;
- employer/organization patterns;
- technology-stack separators;
- links;
- description verb patterns;
- neighbouring lines;
- structured LLM extraction, where configured.

Do not rely solely on one regular expression or on whether a line begins with a bullet.

### 5.1 Lines that are normally details, not entry starts

Attach the following to the current entry where appropriate:
- responsibility bullets;
- achievement/outcome bullets describing the role;
- dates and date ranges;
- organization/company names;
- location and work mode;
- technology stacks, e.g. `Python | Pandas | Scikit-learn`;
- links such as GitHub, Kaggle, portfolio, DOI and publication URLs;
- lines beginning with action verbs such as developed, built, created, implemented, deployed, designed, analyzed, maintained, improved, achieved, worked, assisted, researched, published, presented, or contributed;
- wrapped continuation lines;
- metrics/results such as `99% accuracy`, `30 FPS`, `R² = ...`;
- role metadata such as `Virtual`, `Remote`, `On-site`, `Part-time`.

These details must not independently increase entry counts.

### 5.2 New entry starts

Start a new entry only when there is sufficient evidence, for example:
- a new title/role/credential line with a distinct date or organization nearby;
- a new strongly title-like line with a different semantic role from the previous entry;
- a numbered item explicitly denoting a new item;
- a clear layout boundary (font/position/style) when available;
- a structured LLM entry with exact supporting evidence and a distinct title.

An isolated date or organization line must never start an internship by itself.

### 5.3 Never split one experience into several entries

For this experience group:

```text
EXPERIENCE
AI/ML Intern                                      Jan 2026
Completed a project-based AI/ML internship focused on machine learning workflows and predictive analytics.
Marketing Intern                                  Jun 2026
Recognized for maintaining high standards of professionalism and commitment throughout the internship.
```

Expected result: **2 internships**, not 4.

**Internship 1**
- Title: AI/ML Intern
- Date text: Jan 2026
- Description: Completed a project-based AI/ML internship focused on machine learning workflows and predictive analytics.

**Internship 2**
- Title: Marketing Intern
- Date text: Jun 2026
- Description: Recognized for maintaining high standards of professionalism and commitment throughout the internship.

Also handle:
```text
WORK EXPERIENCE
QSkill
AI/ML Intern | Jan 2026 – Feb 2026
- Built predictive analytics workflows.
- Evaluated model performance.
```

and:
```text
PROFESSIONAL EXPERIENCE
AI/ML Intern
QSkill (Virtual)
Jan 2026 – Feb 2026
- Developed ML workflows.
```

and:
```text
EXPERIENCE
AI/ML Intern — QSkill — Jan 2026
Completed a project-based internship.
Marketing Intern — Company B — Jun 2026
Maintained high standards of professionalism.
```

A new role/title is the entry boundary. Its employer, dates and description are details. Two roles at the same company and with the same title but clearly different date ranges are two entries.

---

## 6. Project extraction: title is the entry, bullets are children

Example:

```text
PROJECTS
Farmer Crop Recommendation System | Python, Scikit-learn, Random Forest, Streamlit | GitHub
- Built a crop recommendation model using 2,200+ agricultural records, achieving 99% accuracy in evaluation.
- Implemented data preprocessing and modular OOP-based design; deployed an interactive Streamlit application for real-time recommendations.
```

Expected: **one project**, not three.

Fields:
- title: `Farmer Crop Recommendation System`
- technologies: Python, Scikit-learn, Random Forest, Streamlit
- links: GitHub URL if present
- description: both bullets joined as one description
- evidence: title line and both bullets

A new project title starts the next entry. A bullet, result, implementation detail, metric, stack or link never starts a new project.

Support:
- `Title | Tech stack | Link`
- `Title — Tech stack`
- `Title: Description`
- title followed by bullets
- wrapped titles and descriptions
- title with date/status metadata

Only split stack/link segments when there is evidence they are metadata. Preserve meaningful title text.

---

## 7. Gemini and local parser reconciliation

Both local parsing and Gemini must produce the same canonical entry schema before the application merges results.

### 7.1 Gemini prompt/schema

Require:
- exactly one entry per distinct real-world project/role/certificate/achievement;
- descriptions, dates, companies, tools, links and metrics as child fields;
- no entry for a bullet or continuation line;
- no entry for date-only or company-only lines;
- internship roles recognized under Experience headings;
- publications/papers/patents under Achievements, never Projects;
- separate projects only with independent implementation evidence;
- exact supporting source text per entry;
- null/unknown rather than invented information.

Prefer one canonical `entries` array with explicit categories, or convert the current response schema immediately into the canonical schema and run a shared normalizer/classifier/deduplicator.

Do not trust the model's category blindly. Apply deterministic category rules and evidence checks after the response.

### 7.2 Local/Gemini merge

Do not simply append one parser's lists to another.

Implement deterministic reconciliation:
1. Normalize whitespace, punctuation and case.
2. Match exact titles first.
3. Use organization/date/source-line overlap as secondary signals.
4. Merge missing metadata and complementary descriptions into one entry.
5. Keep different date ranges as separate roles.
6. Do not merge distinct internships solely because title and employer match.
7. Do not duplicate an entry because both parsers found it.
8. Publications resolve to Achievements when section/type evidence supports that.
9. Preserve both sources/evidence references in audit metadata.

If Gemini is unavailable or invalid, keep the local result and issue a warning. Do not return a half-merged dataset.

---

## 8. Deduplication and identity of entries

A robust match key may combine normalized title, category, organization, date range, source-line/page overlap and normalized evidence.

Rules:
- same title + same employer + same date range + overlapping evidence → likely duplicate;
- same title + same employer but different date ranges → separate roles;
- same project repeated in overlapping OCR chunks → one project;
- same paper title repeated in Publications and Research sections → one achievement unless evidence establishes distinct publications;
- a project and resulting paper with different titles/types → separate category entries if independently evidenced;
- bullets/descriptions never deduplicate against titles as if they were entries.

Keep original evidence for merged records.

---

## 9. Count calculation and CSV compatibility

After normalization, classification, grouping, deduplication and review:

- `Projects` = distinct confirmed project titles.
- `Internships` = distinct internship role entries.
- `Certifications` = distinct credential entries.
- `Achievements` = distinct awards, accomplishments, publications, papers, patents and equivalent records.

Counts must derive from canonical entries, not raw line counts or Gemini fragments.

Important:
- a publication contributes to `Number of Achievements`, not `Number of Projects`;
- internship description bullets do not increase internship count;
- project bullets do not increase project count;
- do not cap counts at model scaling constants;
- preserve existing public CSV columns and their order;
- if CSV stores title lists, serialize one canonical title per entry and keep descriptions/evidence in review metadata or the existing evidence store;
- use safe list serialization/escaping and verify round-tripping;
- do not change trained model feature columns or feature semantics in this task.

A publication subtype may be retained in review/audit metadata while maintaining the existing `Achievements` field for downstream compatibility.

---

## 10. UI and review compatibility

Keep the existing Incepta design and working review flow.

Update entry review cards only as needed:
- Projects show title, technologies, links and description in one card.
- Internships show role title, organization, dates and description in one card.
- Achievements show award/publication/paper title and source details in one card.
- Publications appear under Achievements, not Projects.
- Derived counts reflect entry cards.
- Ambiguous grouping shows a warning, not multiple duplicate cards.
- Experience roles appear in Internships only where role evidence supports internship classification; otherwise keep employment/experience in its appropriate existing view.

Do not add a new confirmation flow or restore any “Confirm no entries” control.

---

## 11. Required automated tests

Create regression tests around `backend/resume_sections.py`, Gemini normalization/reconciliation, and `app.py` count derivation.

### 11.1 Exact duplicate-internship regression fixture

Input:

```text
EXPERIENCE
AI/ML Intern                                      Jan 2026
Completed a project-based AI/ML internship focused on machine learning workflows and predictive analytics.
Marketing Intern                                  Jun 2026
Recognized for maintaining high standards of professionalism and commitment throughout the internship.
```

Expected:
- `Number of Internships == 2`
- titles are exactly `AI/ML Intern` and `Marketing Intern`
- first description is attached to AI/ML Intern
- second description is attached to Marketing Intern
- dates belong to their respective roles
- no description line becomes an internship

### 11.2 Exact project grouping test

Input:

```text
PROJECTS
Farmer Crop Recommendation System | Python, Scikit-learn, Random Forest, Streamlit | GitHub
- Built a crop recommendation model using 2,200+ agricultural records, achieving 99% accuracy in evaluation.
- Implemented data preprocessing and modular OOP-based design; deployed an interactive Streamlit application for real-time recommendations.
Synthetic Employee Performance Dataset | Python, Pandas, HR Analytics | Kaggle
- Created and published a 5,000-record synthetic dataset with employee attributes and performance-related features.
```

Expected:
- exactly two projects;
- first title is `Farmer Crop Recommendation System`;
- both first-project bullets belong to it;
- second title is `Synthetic Employee Performance Dataset`;
- its bullet belongs to it;
- technology stacks and links are metadata, not entries.

### 11.3 Publication routing test

Input:

```text
PROJECTS
Traffic Signal Optimization System | Python, SUMO
- Implemented a traffic simulation and control strategy.

PUBLICATIONS
An Interpretable Physics-Inspired Ensemble Learning Framework for Predicting Nanofluid Thermal Conductivity
- Research paper accepted and presented at an IEEE conference.
```

Expected:
- project count = 1;
- achievement count = 1;
- publication appears under Achievements;
- publication does not appear under Projects.

Test heading variants:
- `Research Publications`
- `Conference Papers`
- `Journal Publications`
- `Awards & Publications`
- `Research Papers`

### 11.4 Other regression tests

- date-only lines never become entries;
- employer-only lines never become entries;
- technology-only lines never become projects;
- links never become projects;
- bullets never become entries;
- normal employment is not automatically an internship;
- training/course is not automatically an internship;
- research implementation remains a project;
- research publication becomes an achievement;
- page/chunk overlap does not duplicate entries;
- same-title internships with different periods remain separate;
- local/Gemini results merge without double counting.

---

## 12. Implementation sequence

1. Inspect existing tests and every call site of `extract_sections`, `parse_resume`, `extract_with_gemini`, and count derivation.
2. Define/refine the canonical entry schema.
3. Refactor `resume_sections.py` for section routing and parent/child grouping.
4. Route publications and research-paper headings into Achievements.
5. Refine Gemini prompt and normalization.
6. Create a shared normalization, classification, merge and deduplication function.
7. Update `app.py` to count only final canonical entries.
8. Keep CSV and model compatibility stable.
9. Update only necessary entry-card mappings.
10. Add regression tests.
11. Run the full test suite and API/integration tests.
12. Report exact files modified and test results.

Do not rebuild the app. Do not remove working OCR, review, validation, export or ML functionality. Do not alter the saved model or retrain it for this parsing-only correction.

---

## 13. Definition of done

- [ ] Two roles in the supplied example produce exactly two internships.
- [ ] Each role's date and description stay attached to that role.
- [ ] Company-only/date-only lines never become standalone internships.
- [ ] Project heading + stack + link + multiple bullets produces one project.
- [ ] Multiple distinct project headings produce the correct count.
- [ ] Research publications, conference papers and journal papers appear in Achievements.
- [ ] Publications do not inflate project counts.
- [ ] Experience headings are searched for internship roles.
- [ ] Normal employment and training are not misclassified without evidence.
- [ ] Local and Gemini results merge without duplicates.
- [ ] Same-title internships with different periods remain separate.
- [ ] Counts derive from final canonical entries after reconciliation.
- [ ] CSV schema and downstream model feature compatibility remain unchanged.
- [ ] Existing Incepta functionality and UI are preserved.
- [ ] Automated regression and full project tests pass.
- [ ] Final report accurately identifies remaining limitations.

---

## 14. Final instruction

**A resume entry is a semantic unit, not a line of OCR text.**

A role title identifies an internship; its employer, dates and responsibilities describe that internship. A project title identifies a project; its technology stack, repository link, metrics and bullets describe that project. A research paper or publication is an achievement, not a project entry.

Implement grouping and classification around that principle, keep evidence traceable, and make the supplied regression examples pass before considering the task complete.
