# AI Fresher Recruitment System --- Application Flow

## 1. High-level flow

``` text
START
  |
  v
HR Login Page
  |
  v
Submit email/password
  |
  v
FastAPI Authentication
  |
  +---- Invalid ----> Show login error
  |
  +---- Valid ------> Admin Dashboard
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
       Resume         Position     Reports
       Screening      Opening
```

## 2. Login flow

1.  HR opens `/login`.
2.  HR enters email and password.
3.  React checks required fields and calls `POST /api/auth/login`.
4.  FastAPI verifies the password hash and account status.
5.  Invalid credentials return an error shown on the login page.
6.  Successful authentication establishes the configured session/token.
7.  React navigates to `/dashboard`.
8.  Protected routes verify authentication before rendering admin pages.

Register opens `/register-preview`. It is a frontend-only employee
registration design and creates no account.

## 3. Dashboard flow

The dashboard contains persistent navigation for Resume Screening,
Position Opening and Reports. It can also show summary cards, recent
screening activity and active openings. Use mock data only during the UI
prototype and label it clearly.

## 4. Position opening flow

``` text
Position Opening
      |
      v
List Existing Openings
      |
      +---- Create New
      |        |
      |        v
      |    Enter Job Details
      |        |
      |        v
      |    Validate Form
      |        |
      |        v
      |    POST /api/jobs
      |        |
      |        v
      |    Save in SQLite
      |        |
      |        v
      |    Show in Opening List
      |
      +---- Select Existing
               |
               v
          View / Edit / Close
```

Only Active openings can be selected for screening.

## 5. Resume screening flow

``` text
Resume Screening
       |
       v
Select Active Job Opening
       |
       v
Click "Select Resume"
       |
       v
Choose PDF from Computer
       |
       v
Validate File in Browser
       |
       v
Show PDF Preview
       |
       v
HR Clicks "Screen Resume"
       |
       v
Upload PDF + job_id to FastAPI
       |
       v
Backend Validates PDF
       |
       v
Create Screening Record
       |
       v
Extract PDF Text
       |
       v
Extract Candidate Information
       |
       v
Convert and Validate JSON
       |
       v
Analyze Skills, Education,
Projects, Internships,
Certificates and Achievements
       |
       v
Calculate Job-specific Score
       |
       v
Save Results in Database
       |
       v
Show Result to HR
       |
       v
HR Reviews Resume and Evidence
       |
       v
Record HR Review Status/Notes
```

## 6. Processing screen

  -----------------------------------------------------------------------
  Stage                   Backend work            UI status
  ----------------------- ----------------------- -----------------------
  Uploading Resume        Receive PDF and job ID  Pending / In Progress /
                                                  Completed

  Validating Resume       Check type, size and    Pending / In Progress /
                          readability             Completed / Failed

  Extracting Text         Read PDF text           Pending / In Progress /
                                                  Completed / Failed

  Extracting Data         Identify candidate      Pending / In Progress /
                          fields                  Completed / Failed

  Converting to JSON      Normalize and validate  Pending / In Progress /
                          schema                  Completed / Failed

  Skill Analysis          Compare candidate and   Pending / In Progress /
                          job skills              Completed / Failed

  Certificate Analysis    Extract and assess      Pending / In Progress /
                          certificate relevance   Completed / Failed

  Experience Analysis     Review projects,        Pending / In Progress /
                          internships and         Completed / Failed
                          experience              

  Score Calculation       Calculate score and     Pending / In Progress /
                          component breakdown     Completed / Failed

  Saving Results          Persist screening       Pending / In Progress /
                          record                  Completed / Failed

  Completed               Result ready for review Completed
  -----------------------------------------------------------------------

If a stage fails, show the failed stage and a useful message. Do not
mark later stages completed. For long tasks, React polls
`/api/screenings/{id}/status`. A short synchronous prototype can return
a completed response directly.

## 7. Result page

Display: 1. Candidate details found in the PDF. 2. Job opening screened
against. 3. Overall screening score and provisional/final status. 4.
Score coverage and component breakdown. 5. Extracted education and
skills. 6. Projects and internships. 7. Certifications and achievements.
8. Missing information and extraction warnings. 9. Original PDF preview
for authorized HR. 10. HR review status and notes.

The score is decision support only. HR should inspect the original
resume and extracted evidence before deciding.

## 8. Reports flow

``` text
Reports Page
     |
     v
React requests report APIs
     |
     +---- GET /api/reports/summary
     +---- GET /api/reports/by-job
     +---- GET /api/reports/activity
     |
     v
FastAPI queries SQLite
     |
     v
Return aggregated JSON
     |
     v
React renders cards, tables and charts
```

Suggested reports: total resumes screened, active openings, screening
count by job, average score by job, HR review status distribution,
processing failures and screening activity over time.

## 9. Frontend route map

  --------------------------------------------------------------------------------------
  Screen                  Route                                  Access
  ----------------------- -------------------------------------- -----------------------
  HR Login                `/login`                               Public

  Employee Register       `/register-preview`                    Public, demo only
  Preview                                                        

  Admin Dashboard         `/dashboard`                           Authenticated HR

  Resume Screening        `/resume-screening`                    Authenticated HR

  Processing              `/screening/:screeningId/processing`   Authenticated HR

  Screening Result        `/screening/:screeningId/result`       Authenticated HR

  Position Openings       `/position-openings`                   Authenticated HR

  Create Opening          `/position-openings/new`               Authenticated HR

  Edit Opening            `/position-openings/:jobId/edit`       Authenticated HR

  Reports                 `/reports`                             Authenticated HR
  --------------------------------------------------------------------------------------

## 10. Keep two statuses separate

**Processing status:** `queued`, `uploading`, `validating`,
`extracting_text`, `parsing`, `analyzing`, `scoring`, `saving`,
`completed`, `failed`.

**HR review status:** `pending`, `reviewed`, `shortlisted`, `rejected`.

A screening can be processing `completed` while HR review remains
`pending`.

## 11. Error and empty states

Design for: - No active job openings. - No PDF selected. - Non-PDF
file. - File too large. - Password-protected/unreadable PDF. - Scanned
PDF with no extractable text. - Some fields missing. - Processing
failure. - Screening record not found. - Expired HR session. - Reports
with no data.

For scanned/image-only PDFs, ordinary PDF text extraction may return
little or no text. Display that clearly; OCR can be added later.

## 12. Complete HR journey

1.  HR logs in.
2.  HR creates or selects an active job opening.
3.  HR opens Resume Screening and selects the job.
4.  HR selects a PDF resume and previews it.
5.  HR clicks Screen Resume.
6.  The processing screen shows actual backend stages.
7.  FastAPI extracts text and candidate information.
8.  Extracted information is normalized into validated JSON.
9.  The scoring engine calculates a job-specific score and explanation.
10. The result page displays score, extracted data, missing fields and
    warnings.
11. HR reviews the original resume and extracted evidence.
12. HR records a review status and notes.
13. The screening record appears in history and reports.
