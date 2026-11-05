# AI Fresher Recruitment System --- Backend and Frontend

## 1. Recommended stack

**Frontend:** React + Vite, React Router, Axios (or Fetch), Tailwind
CSS, `react-pdf` for PDF preview, Recharts for charts (optional).

**Backend:** Python + FastAPI, Pydantic, SQLAlchemy, SQLite,
`python-multipart`, PyMuPDF (`fitz`) or `pdfplumber` for PDF text
extraction, password hashing, and JWT or secure server-side sessions.

**Database recommendation:** Start with **SQLite**. It is file-based,
easy to set up, and suitable for a single-machine prototype/college
project. Move to PostgreSQL if you need production deployment, multiple
concurrent users, or stronger operational scalability. Use SQLAlchemy so
database migration is easier. Store PDF files in a dedicated storage
folder and store only metadata/path in SQLite.

## 2. Suggested folder structure

``` text
ai-fresher-recruitment/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Navbar.jsx
│       │   ├── ProtectedRoute.jsx
│       │   ├── PdfPreview.jsx
│       │   ├── ProcessingStepper.jsx
│       │   └── ScoreBreakdown.jsx
│       ├── pages/
│       │   ├── Login.jsx
│       │   ├── EmployeeRegisterPreview.jsx
│       │   ├── Dashboard.jsx
│       │   ├── ResumeScreening.jsx
│       │   ├── ScreeningProcessing.jsx
│       │   ├── ScreeningResult.jsx
│       │   ├── PositionOpenings.jsx
│       │   └── Reports.jsx
│       ├── services/
│       │   ├── api.js
│       │   ├── authService.js
│       │   ├── jobService.js
│       │   └── resumeService.js
│       ├── App.jsx
│       └── main.jsx
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── jobs.py
│   │   │   ├── resumes.py
│   │   │   └── reports.py
│   │   ├── services/
│   │   │   ├── pdf_extractor.py
│   │   │   ├── resume_parser.py
│   │   │   ├── skill_matcher.py
│   │   │   ├── scoring_engine.py
│   │   │   └── screening_service.py
│   │   ├── security/
│   │   ├── uploads/
│   │   └── tests/
│   ├── requirements.txt
│   └── .env
└── README.md
```

Introduce folders gradually; do not create all files before the first
screen works.

## 3. Frontend screens

### HR Login --- `/login`

-   Email and password fields, Login button, Register button, validation
    and error messages.
-   Login calls `POST /api/auth/login`.
-   On success, navigate to `/dashboard`.
-   Register opens `/register-preview`; this is a frontend-only demo and
    does not create an employee account.
-   For production, prefer an HttpOnly, Secure, SameSite cookie. Avoid
    long-lived tokens in localStorage.

### Employee Register Preview --- `/register-preview`

Show full name, work email, employee ID, department, password and
confirm password as design placeholders. Label the page `Demo only`; do
not submit it to the backend.

### Admin Dashboard --- `/dashboard`

Persistent navbar/sidebar with: 1. Resume Screening 2. Position Opening
3. Reports

Main area: summary cards, recent screening activity, active openings and
a quick screen-resume action.

### Resume Screening --- `/resume-screening`

-   Job-opening dropdown (required).
-   Select Resume button; PDF only.
-   Filename and file size.
-   PDF preview panel.
-   Remove/change file.
-   Screen Resume button.

Create a browser object URL for preview and revoke it when the file
changes or component unmounts. Enable screening only when both an active
job and a valid PDF are selected. Upload the PDF and `job_id` to
FastAPI.

### Processing --- `/screening/:screeningId/processing`

Display real processing stages: Uploading, Validating, Extracting Text,
Extracting Details, Converting to JSON, Skill Analysis, Certificate
Analysis, Experience Analysis, Score Calculation, Saving, Completed. Use
statuses Pending/In Progress/Completed/Failed. For longer tasks, poll a
status endpoint. Do not show fake completion using a timer.

### Screening Result --- `/screening/:screeningId/result`

Show candidate details found, selected job, overall score, score
coverage, provisional status, component score breakdown, education,
skills, projects, internships, certifications, achievements, missing
fields, warnings, and authorized PDF preview. Add HR review status and
notes. Include:
`Screening score is decision support. Review the original resume and extracted evidence before making a decision.`

### Position Opening --- `/position-openings`

List Draft/Active/Closed openings. Support create, edit, view, activate
and close. Fields: title, department, description, required/preferred
skills, preferred degree, optional CGPA/experience, number of openings
and status.

### Reports --- `/reports`

Start with clearly labelled placeholders for total resumes screened,
active openings, screenings by job, average score by job, HR review
status, processing success/failure and activity over time. Replace mock
data with API data later.

## 4. Backend responsibilities

-   **Authentication:** verify HR credentials, hash passwords, manage
    sessions/tokens, protect admin routes. Seed a development HR
    administrator; do not expose public HR registration.
-   **Job service:** create/list/get/update openings, change status, and
    ensure a job is active before screening.
-   **Resume service:** validate/store PDF, calculate hash, create
    records, extract text, parse structured fields, save warnings.
-   **Scoring service:** load job requirements, normalize skills,
    calculate component scores, handle unavailable fields, return score
    breakdown and configuration version.

Use the transparent job-specific score initially. The previous synthetic
classifier should not be treated as a production hiring model without
validation on representative, consented real-world data and a fairness
review.

## 5. API endpoints

Base prefix: `/api`

### Authentication

  Method   Endpoint         Purpose
  -------- ---------------- -----------------
  POST     `/auth/login`    HR login
  POST     `/auth/logout`   End session
  GET      `/auth/me`       Current HR user

No employee registration API in this phase.

### Jobs

  Method   Endpoint                  Purpose
  -------- ------------------------- ----------------
  GET      `/jobs`                   List openings
  POST     `/jobs`                   Create opening
  GET      `/jobs/{job_id}`          Get opening
  PUT      `/jobs/{job_id}`          Update opening
  PATCH    `/jobs/{job_id}/status`   Activate/close

### Screening

  Method   Endpoint                              Purpose
  -------- ------------------------------------- --------------------------------
  POST     `/screenings`                         Upload PDF and start screening
  GET      `/screenings/{screening_id}`          Get result
  GET      `/screenings/{screening_id}/status`   Processing status
  GET      `/screenings`                         Screening history
  PATCH    `/screenings/{screening_id}/review`   HR review status/notes
  GET      `/screenings/{screening_id}/resume`   Authorized PDF retrieval

`POST /screenings` uses multipart form data with `job_id` and `file`.

### Reports

  Method   Endpoint              Purpose
  -------- --------------------- ----------------------------
  GET      `/reports/summary`    Dashboard summary
  GET      `/reports/by-job`     Counts and score summaries
  GET      `/reports/activity`   Activity over time

## 6. Example response

``` json
{
  "screening_id": 123,
  "status": "completed",
  "candidate": {"full_name": "Example Candidate", "email": null, "phone": null},
  "job": {"job_id": 4, "job_title": "Python Developer"},
  "score": {
    "overall_score": 78.4,
    "score_status": "provisional",
    "score_coverage": "6 of 8 components available",
    "components": {},
    "warnings": []
  },
  "extracted_data": {},
  "created_at": "2026-11-05T16:00:00Z"
}
```

Illustrative values only.

## 7. SQLite tables

Start with `users`, `jobs`, `candidates`, `resumes`, and `screenings`.
One candidate can have many resumes; one resume can be screened against
multiple jobs; one job has many screenings. Store extracted JSON and
score breakdown as JSON text initially. Add foreign keys and indexes on
email, job_id, candidate_id, status and upload date.

## 8. Upload security

-   Check PDF extension, MIME type and PDF signature; do not trust
    filename alone.
-   Set maximum upload size.
-   Generate a random server filename; never use user filename as a
    storage path.
-   Keep uploads outside the public frontend directory.
-   Prevent path traversal.
-   Restrict PDF retrieval to authenticated HR users.
-   Consider malware scanning before production.
-   Do not log resume contents, personal contact details, passwords or
    tokens.
-   Define retention/deletion rules.
-   Use HTTPS in deployment.
-   Keep `.env`, real resumes and databases containing personal data out
    of Git.

## 9. Local setup

### Backend

``` bash
cd backend
python -m venv .venv
```

Windows PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
pip install fastapi uvicorn sqlalchemy pydantic python-multipart pymupdf
uvicorn app.main:app --reload
```

FastAPI docs: `http://127.0.0.1:8000/docs`

### Frontend

``` bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install react-router-dom axios
npm run dev
```

Add Tailwind, PDF preview and chart libraries when those features are
implemented.

## 10. Configuration

Use environment variables such as `DATABASE_URL`, `SECRET_KEY`,
`UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, and `CORS_ORIGINS`. Keep secrets out
of source control.
