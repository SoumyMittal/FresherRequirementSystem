# AI Fresher Recruitment System --- System Logic

## 1. Purpose

An HR-facing decision-support application for managing job openings,
uploading PDF resumes, extracting structured candidate information,
calculating a job-specific screening score, and presenting results for
human review. The system assists HR; it does not make final hiring
decisions.

## 2. Scope

Included: HR login, frontend-only employee registration preview, admin
dashboard, Resume Screening, Position Opening, Reports, PDF
preview/upload, extraction, JSON conversion,
skill/certificate/education/experience analysis, score breakdown,
screening history and HR review. Not included initially: employee
portal/backend registration, video or facial analysis, automatic
hiring/rejection, production enterprise identity management.

## 3. Actors

-   **HR Administrator:** authenticates, manages openings, screens
    resumes, reviews results and reports.
-   **Employee (prototype only):** Register button opens a designed
    preview page; no account is created.

## 4. Core data entities

-   **User:** id, name, email, password_hash, role, created_at.
-   **Job:** id, title, department, description, required_skills,
    preferred_skills, preferred_degree, optional
    minimum_cgpa/experience, number_of_openings, status, timestamps.
-   **Candidate:** id, full_name, email, phone, created_at.
-   **Resume:** id, candidate_id, original_filename, stored_filename,
    file_path, SHA-256 file_hash, mime_type, file_size, uploaded_at,
    extraction_status.
-   **Screening/Application:** id, candidate_id, resume_id, job_id,
    processing_status, score, score_breakdown_json, extracted_data_json,
    missing_fields_json, HR_review_status, created_at.

A candidate can have multiple resumes and applications. A resume may be
screened against different jobs and should receive a job-specific score.

## 5. End-to-end logic

1.  HR opens Login and submits credentials.
2.  FastAPI verifies credentials; successful login redirects React to
    the Admin Dashboard.
3.  HR creates or selects an active job opening.
4.  HR opens Resume Screening, selects the job, and chooses a PDF.
5.  React validates basic file properties and shows a local PDF preview.
6.  HR clicks **Screen Resume**.
7.  React uploads the PDF and job ID to FastAPI.
8.  Backend validates and stores the PDF, creates a screening record,
    and extracts text.
9.  Parser extracts candidate details and converts them into a
    consistent JSON structure.
10. Backend normalizes skills and analyzes education, projects,
    internships, certificates and achievements.
11. Scoring engine compares the candidate with the selected job
    requirements.
12. Backend stores the extracted data, score, component breakdown,
    warnings and processing status.
13. React displays the result to HR.
14. HR checks the original PDF, corrects extraction errors if supported,
    and records a review decision.

## 6. Processing stages displayed in the UI

1.  Uploading Resume
2.  Validating Resume
3.  Extracting Text
4.  Extracting Candidate Details
5.  Converting Data to JSON
6.  Analyzing Skills
7.  Certificate Analysis
8.  Analyzing Education and Experience
9.  Calculating Screening Score
10. Saving Results
11. Completed

Use statuses `Pending`, `In Progress`, `Completed`, `Failed`. These must
reflect backend progress, not just a fake frontend timer. For long
processing jobs, use a background task and status polling endpoint.

## 7. Structured resume JSON

Fields not found must be null, empty lists, or explicitly marked
missing. Never invent candidate information.

``` json
{
  "personal_information": {
    "full_name": null, "email": null, "phone": null,
    "location": null, "linkedin": null, "github": null, "portfolio": null
  },
  "education": [{
    "degree": null, "specialization": null, "institution": null,
    "start_year": null, "end_year": null, "cgpa": null, "percentage": null
  }],
  "skills": [],
  "projects": [],
  "internships": [],
  "work_experience": [],
  "certifications": [],
  "achievements": [],
  "extraction_metadata": {
    "extraction_status": "pending", "missing_fields": [], "warnings": []
  }
}
```

## 8. Screening score logic

### Important model decision

The earlier classifier was trained on synthetic labels created from a
manually designed score, and its test performance was notably weaker
than validation performance. Do not present it as a proven real-world
hiring predictor. For the first implementation, use a transparent,
job-specific scoring engine. The earlier weights can be used as a
prototype configuration:

  Component                  Weight
  ---------------------- ----------
  Required skill match          35%
  CGPA                          20%
  Projects                      15%
  Internships                   10%
  Certifications                 5%
  Achievements                   5%
  Degree match                   5%
  Backlog score                  5%
  **Total**                **100%**

Definitions: - Required skill match = matched required skills / total
required skills. - CGPA = normalized CGPA only when reliably extracted
and relevant to the opening. - Projects/internships = relevance and
evidence, not just raw counts. - Certifications = relevance and
validity, not simply number of certificates. - Degree match = comparison
with the opening's stated degree requirements. - Backlogs: resumes
usually do not state this. Never assume missing backlog information
means zero or penalize its absence.

### Missing information

Store unavailable component values as null and mark them
`Not Available`. Either re-normalize weights across available/applicable
components or mark the score provisional. Show score coverage (for
example, 6 of 8 components available) and warnings. HR must be able to
see what evidence contributed to the score.

Example score response:

``` json
{
  "overall_score": 78.4,
  "score_status": "provisional",
  "score_coverage": "6 of 8 components available",
  "components": {
    "skill_match": {
      "score": 0.85, "weight": 0.35,
      "weighted_contribution": 29.75, "status": "available"
    },
    "backlogs": {
      "score": null, "weight": 0.05,
      "weighted_contribution": null, "status": "not_available"
    }
  },
  "warnings": ["Backlog information was not present in the resume."]
}
```

Numbers are illustrative only.

### Fairness and human review

Do not score using photos, names, addresses, gender, age, religion,
caste, health, or inferred personality/confidence. Do not infer honesty,
intelligence or other sensitive traits. Show evidence and extraction
warnings, allow HR correction, keep score-configuration versions and
manual overrides, and never automatically reject based only on the
score.

## 9. Duplicate handling

Use a SHA-256 hash to detect an exact duplicate PDF. Similar names alone
do not prove two resumes belong to the same person. Email can identify
possible duplicates for HR review.

## 10. Reports

Initial report cards/charts: total resumes screened, active openings,
screening count by job, average score by job, review-status
distribution, processing success/failure, and screening activity over
time. Label mock data as mock data.

## 11. Implementation phases

1.  React layouts and navigation with mock data.
2.  FastAPI authentication and job APIs.
3.  PDF selection and preview.
4.  PDF upload and text extraction.
5.  Structured JSON extraction and validation.
6.  Transparent job-specific scoring.
7.  Result page and screening history.
8.  Reports, testing, security and deployment.
