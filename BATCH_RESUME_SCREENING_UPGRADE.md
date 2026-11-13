# Sprout --- Batch Resume Screening Upgrade

## Product Requirements and Implementation Specification

**Repository:** `SoumyMittal/FresherRequirementSystem`\
**Target branch:** `main`\
**Document purpose:** Define the next cohesive upgrade to Sprout's
resume extraction, batch assessment, candidate routing, and HR workflow.

------------------------------------------------------------------------

## 1. Objective

Replace the current per-resume review-and-predict workflow with a
batch-oriented recruitment workflow.

The desired HR journey is:

1.  Select a job opening.
2.  Upload multiple candidate resumes.
3.  Extract all uploaded resumes automatically.
4.  Review the extraction summary.
5.  Click **Run Model on All Resumes** once.
6.  Run validation, preprocessing, feature engineering, inference,
    scoring, and job-specific ranking in batches.
7.  Automatically route eligible model-shortlisted candidates to **HR
    Shortlist**.
8.  Route candidates with invalid, out-of-bound, ambiguous, or
    unreliable extracted data to **Need Data Review**.
9.  Keep valid non-shortlisted candidates in the general candidate pool.
10. Let HR make and record the final hiring decision.

The system must not require HR to open and confirm every successfully
extracted resume before running the model. Human review should be
exception-based, while preserving access to the source resume and
extracted evidence.

## 2. Core workflow

``` mermaid
flowchart TD
    A["HR selects job opening"] --> B["Upload multiple resumes"]
    B --> C["Batch extraction queue"]
    C --> D["Text extraction / OCR"]
    D --> E["Local parser + optional Gemini"]
    E --> F["Normalize candidate profiles"]
    F --> G["Validate fields and detect duplicates"]
    G --> H["Extraction summary"]
    H --> I["HR clicks Run Model on All Resumes"]
    I --> J["Prepare model-ready records"]
    J --> K["Shared feature engineering pipeline"]
    K --> L["Batch ML inference"]
    L --> M["Recruitment scoring"]
    M --> N["Job-specific ranking"]
    N --> O{"Assessment result"}
    O -->|"Shortlisted"| P["HR Shortlist"]
    O -->|"Not shortlisted"| Q["General candidate pool"]
    G -->|"Invalid / out-of-bound / unreliable"| R["Need Data Review"]
    R --> S["HR corrects affected fields"]
    S --> H
    P --> T["HR final decision"]
```

## 3. Requirement A --- Batch resume upload and extraction

### Expected behaviour

-   Allow HR to upload multiple PDF resumes in one batch.
-   Associate the batch with one selected job opening.
-   Extract all uploaded resumes automatically without requiring the
    user to open each resume.
-   Use embedded PDF text extraction first and OCR for scanned or
    insufficient-text pages.
-   Use the existing local parser and optional Gemini parser where
    configured.
-   Keep Gemini optional: extraction must continue using the local
    parser when no API key is configured.
-   Extract profile and recruitment information, including:
    -   Name and email, where present.
    -   Degree and specialization.
    -   CGPA.
    -   Class 10 and Class 12 percentages.
    -   Backlogs.
    -   Skills.
    -   Projects.
    -   Internships and work experience.
    -   Certifications.
    -   Achievements and publications.
-   Preserve source evidence and original resume association for
    extracted fields and grouped entries.
-   Assign a stable application/screening identifier to each resume.
-   Show genuine backend processing progress and per-file status. Do not
    simulate progress with fake timers.
-   A failed resume must not stop other resumes in the batch.
-   Support retrying failed documents without rerunning successful
    extraction unnecessarily.
-   Prevent accidental duplicate processing when a user retries or
    refreshes.

### Extraction summary

After extraction, show counts for: - Successfully extracted. - Partially
extracted. - Failed extraction. - Ready for model assessment. - Need
Data Review. - Duplicate or possible duplicate.

Provide a single **Run Model on All Resumes** action after extraction
has completed. The action should clearly show how many eligible profiles
will be assessed and how many are excluded pending review.

## 4. Requirement B --- One-click batch model execution

When HR clicks **Run Model on All Resumes**:

1.  Select the eligible extracted records for the chosen job and batch.
2.  Validate the records again on the server. Do not trust frontend
    validation.
3.  Apply the documented missing-value policy.
4.  Generate the exact raw input contract expected by the existing
    shared recruitment pipeline.
5.  Run feature engineering using the existing canonical feature
    implementation.
6.  Run inference with the existing saved model, provided its input
    contract and preprocessing compatibility are verified.
7.  Calculate the separate weighted recruitment score.
8.  Generate deterministic, job-specific ranks.
9.  Persist model run metadata and candidate outcomes.
10. Route candidates to the appropriate application sections.

### Batch behaviour

-   Use vectorized/batch inference where supported; do not make an
    independent model-run request for each candidate.
-   Preserve application IDs and source resume associations.
-   A single bad record must not crash the whole batch.
-   Record per-record errors and continue processing other eligible
    records.
-   Make retries idempotent or clearly versioned so candidates are not
    duplicated.
-   Prevent accidental repeated runs from creating duplicate shortlist
    entries.
-   Store a model-run/batch identifier and timestamp.
-   Show a final summary of assessed, shortlisted, non-shortlisted, and
    failed records.

### Model score and recruitment score

Keep these measures distinct: - **ML shortlist score/class/segment:**
output from the saved classifier and its configured threshold. -
**Weighted recruitment score:** the separate deterministic recruitment
score. - **Job-specific rank:** rank within the selected job and
relevant batch/pool.

Do not label an uncalibrated classifier score as a real-world hiring
probability. Do not silently change the model threshold, model weights,
feature order, or scoring equation as part of this workflow upgrade.

## 5. Requirement C --- Candidate routing and HR sections

### HR Shortlist

Automatically place candidates who meet the configured model-shortlist
rule into the HR Shortlist section.

Show, at minimum: - Candidate name and application ID. - Selected job. -
ML score and model segment. - Weighted recruitment score. - Job-specific
rank. - Extraction/assessment timestamp. - Resume access. - Extracted
profile and evidence. - HR decision and decision history.

The HR Shortlist is a queue for human review, not an automatic final
hiring decision.

### General candidate pool

Candidates who were validly assessed but did not meet the configured
shortlist rule must remain visible in the general candidate pool as
non-shortlisted candidates.

They must not be placed in HR Shortlist merely because they have a high
weighted recruitment score if the actual shortlist rule is based on the
classifier, unless the product owner explicitly changes that rule.

### Need Data Review

Use this section only for records that cannot be safely assessed because
of: - Out-of-bound numerical values. - Malformed or contradictory
values. - Ambiguous or unreliable extraction. - Incorrect field
mapping. - Unreadable or insufficient source evidence for a required
field. - Other validation failures that make the model input unsafe or
misleading.

For each affected candidate, show: - The field needing attention. -
Extracted value. - Validation/review reason. - Source evidence or page
reference where available. - Suggested correction only when it can be
grounded in the resume. - HR correction control. - Revalidate and
return-to-batch action.

Do not send every missing optional field to Need Data Review. Missing
values that can safely use the agreed model-input defaults should be
defaulted and assessed, subject to the model-compatibility checks below.

After HR corrects a record, revalidate it and allow it to be included in
a subsequent batch model run. Preserve the original extracted value and
correction history.

## 6. Requirement D --- Missing-value policy

The requested model-ready defaults are:

### Numerical columns

Use `0` for missing numerical values in the model-ready record,
including: - CGPA. - Class 10 percentage. - Class 12 percentage. -
Backlogs. - Project count. - Internship count. - Certification count. -
Achievement count. - Other numerical fields only where zero is a valid,
documented default.

### Text columns

Use the exact string `Not Provided` for missing text values in the
model-ready record, including: - Degree. - Specialization. - Skills. -
Other optional text fields. - List/text fields where the downstream
schema explicitly supports this representation.

Do not insert the literal string `Not Provided` into a list if the
schema expects a list of entries. Follow the canonical schema and model
adapter.

### Critical distinction: missing versus genuine zero/empty

The system must distinguish: 1. A value explicitly stated as zero. 2. A
value genuinely absent from the resume. 3. A value that could not be
extracted. 4. A value that was extracted but is invalid or out of
bounds. 5. An explicitly empty section (for example, the resume clearly
states no projects).

Never treat parser failure as proof that a candidate has no projects,
internships, skills, or achievements.

### Preserve provenance

Maintain separate representations for: - Original resume/source. - Raw
extracted value. - HR-corrected value, if any. - Model-ready normalized
value. - Missingness/provenance indicator.

Never overwrite the original extracted value when applying defaults.

### Model compatibility is mandatory

The current saved Logistic Regression artifact was trained using a
particular preprocessing pipeline and feature contract. Changing
missing-value handling from the training-time strategy to
zero/`Not Provided` may change the input distribution and predictions.

Before enabling the new defaults for inference: - Inspect the saved
artifact's preprocessing pipeline and expected feature names/order. -
Verify whether `Not Provided` is accepted by the fitted text/categorical
preprocessing. - Verify numeric zero handling and scaling behaviour. -
Compare the current adapter's output with the artifact's exact expected
input. - Run regression and parity tests. - Quantify prediction changes
on representative fixtures.

If the new defaults are incompatible or materially distort model
behaviour, do not silently force them into the current model.
Update/retrain and validate the model with a matching preprocessing
strategy, or introduce a documented compatibility adapter. Keep the
user-requested model-ready defaults visible in the data contract while
preserving model-safe transformations as a separate, auditable layer.

### Eligibility safeguards

A missing CGPA defaulted to zero must not be confused with a candidate
whose actual CGPA is zero. Do not automatically reject a candidate
solely because an unknown value was defaulted. Preserve a missingness
indicator and apply explicit eligibility rules that distinguish unknown
from known values.

## 7. Requirement E --- Validation and extraction quality

Implement field-level validation with clear, explainable reasons.

Examples: - CGPA above the permitted scale: out of bounds. - Percentage
outside 0--100: out of bounds. - Negative backlog count: invalid. -
Malformed email: invalid profile field, but should not necessarily block
model inference if email is not a model input. - Ambiguous degree or
specialization: review if required by the model/job rule. - Uncertain
OCR value: review when it affects a required model input. - Missing
optional field: use the documented default where safe.

Validation should be schema-driven and consistent between: - Resume
uploads. - HR corrections. - CSV imports. - Batch inference.

Avoid inventing extracted values. Gemini or local parsing must leave
unsupported values unknown and provide warnings/evidence.

## 8. Requirement F --- Duplicate detection

Add duplicate checks at two levels:

### Exact document duplicate

-   Use a cryptographic hash of the uploaded file.
-   Detect the same PDF uploaded again.
-   Avoid creating duplicate application records for accidental
    re-uploads.

### Possible same-candidate duplicate

-   Use normalized email as a strong matching signal where available.
-   Use normalized name and other available profile attributes as
    supporting signals.
-   Do not merge candidates based only on a matching name.
-   Preserve distinct applications when the same person applies to
    different jobs.
-   Show possible duplicates for HR review rather than silently merging
    uncertain matches.

## 9. Requirement G --- Job-specific screening and ranking

-   Every batch must be associated with a selected job.
-   Use that job's required skills, preferred degree, minimum CGPA, and
    opening information where applicable.
-   Rank candidates within the relevant job, not across unrelated roles.
-   Keep job requirements and model output separate.
-   Recompute or invalidate affected assessments if job requirements or
    confirmed candidate data change.
-   Do not change the saved model's training feature contract without an
    explicit model migration/retraining plan.

## 10. Requirement H --- HR decision management

Keep ML assessment separate from HR decisions.

Suggested HR decision states: - Pending HR Review. - Under Review. -
Selected. - Rejected. - On Hold.

Rules: - Model inference must never automatically mark a candidate as
Selected or Rejected. - Re-running the model must not overwrite an
existing HR decision. - Record who made a decision when authentication
exists, decision timestamp, and optional reason. - Preserve decision
history.

## 11. Requirement I --- Auditability and persistence

Persist enough information to reproduce and explain an assessment: -
Original resume file and file hash. - Extracted text/OCR output, subject
to appropriate retention/privacy policy. - Raw extracted fields and
evidence. - HR corrections and history. - Model-ready normalized
record. - Validation results and warnings. - Feature schema/version. -
Model artifact/version/hash. - Model threshold/configuration. - ML
output and weighted recruitment score. - Job ID and job-requirement
version. - Batch/model-run ID and timestamps. - Candidate routing
status. - HR decision history.

Use the existing persistence architecture for the first implementation
unless a database migration is explicitly approved. Do not introduce
SQLite or another database as an incidental part of this task.

## 12. User interface changes

### Resume Studio

-   Batch upload and selected job.
-   Per-file extraction progress/status.
-   Extraction summary.
-   Clear eligible and review-required counts.
-   One **Run Model on All Resumes** button.
-   Disable the button while extraction is incomplete or a run is
    already active.
-   Explain which records will be assessed and which are excluded
    pending review.
-   Display batch completion summary and links to results.

### HR Shortlist

-   Automatically populated after batch inference.
-   Search, sort, filter, and job-specific ranking.
-   Candidate detail and resume preview.
-   ML score and weighted score shown separately.
-   HR decision controls.

### Need Data Review

-   Only invalid, out-of-bound, ambiguous, or unreliable records.
-   Field-level reason and source evidence.
-   Edit/correct, validate, and resubmit controls.
-   Preserve correction history.

### General candidate pool

-   Keep valid non-shortlisted candidates visible.
-   Clearly distinguish not shortlisted from not assessed and needs
    review.

## 13. Non-functional requirements

-   Preserve existing working functionality unless a change is required
    by this specification.
-   Keep backend validation authoritative.
-   Handle partial failures and retries safely.
-   Avoid duplicate records and duplicate shortlist entries.
-   Keep batch processing bounded and configurable; do not load an
    unlimited number of large PDFs into memory at once.
-   Keep API keys server-side and never expose them to frontend code or
    logs.
-   Do not expose the current demo authentication as production
    security.
-   Preserve accessibility, responsive layout, and reduced-motion
    support.
-   Provide clear errors without leaking secrets or sensitive server
    details.
-   Respect privacy and retention requirements for candidate resumes and
    personal data.

## 14. Testing and acceptance criteria

The implementation is complete only when the following are verified.

### Batch extraction

-   Upload multiple text-based PDFs and confirm all are extracted
    automatically.
-   Upload scanned and mixed PDFs and confirm OCR is used as needed.
-   Confirm one failed PDF does not stop other files.
-   Confirm retry does not duplicate successful records.
-   Confirm extraction evidence remains linked to the correct resume.

### Batch model execution

-   After extraction, one action runs inference for all eligible
    profiles.
-   The backend performs batch processing through the shared pipeline.
-   The correct selected job is attached to every application.
-   Invalid records are isolated and reported.
-   Repeated clicks cannot create duplicate results or shortlist
    entries.
-   Output feature order and values match the saved artifact contract.

### Routing

-   Model-shortlisted candidates appear in HR Shortlist.
-   Valid non-shortlisted candidates remain in the general candidate
    pool.
-   Invalid/out-of-bound/unreliable records appear in Need Data Review.
-   Missing optional values handled by approved defaults do not
    automatically trigger review.
-   HR decisions are not changed by model runs.

### Missing values

-   Missing numeric fields receive the agreed model-ready zero default.
-   Missing text fields receive `Not Provided` in the agreed model-ready
    representation.
-   Genuine zero and missing values remain distinguishable.
-   Original extracted data is preserved.
-   Out-of-bound values are not silently replaced with zero.
-   Model compatibility and prediction regression tests pass.

### Duplicate handling

-   Exact duplicate files are detected.
-   Possible same-candidate matches are flagged safely.
-   Same candidate applying to different jobs can have distinct
    applications.

### Regression

-   Existing CSV pipeline tests pass.
-   Existing resume extraction and OCR tests pass.
-   Existing Gemini parser tests pass.
-   Existing workflow and browser tests pass or are deliberately updated
    with documented reasons.
-   No original dataset or saved model is overwritten without approval.
-   No database migration or unrelated redesign is introduced.

## 15. Implementation guidance

Work incrementally and inspect the current repository before editing.

Recommended sequence: 1. Map the existing resume upload, screening,
pipeline, persistence, and frontend flows. 2. Identify the current
manual confirmation gate and all routes that depend on it. 3. Design
batch/job/application state transitions. 4. Implement backend batch
orchestration and idempotency. 5. Implement field-level validation and
missing-value provenance. 6. Verify saved-model preprocessing
compatibility before changing inference defaults. 7. Implement candidate
routing and persistence. 8. Update Resume Studio, HR Shortlist, Need
Data Review, and general candidate pool. 9. Add automated tests for
happy paths, partial failures, retries, duplicates, invalid data, and
routing. 10. Run all backend and browser tests and document exact
results.

Do not: - Replace the existing ML model without approval. - Change the
model threshold or scoring formula without approval. - silently treat
unknown academic values as genuine zero for eligibility. - automatically
reject candidates. - remove original source evidence. - send every
candidate to manual review. - create fake progress indicators. -
introduce a database migration as part of this task. - claim tests
passed unless they were actually run.

------------------------------------------------------------------------

# 16. Prompt for the coding agent

Use the following prompt with the repository open in your coding agent
(for example, Antigravity, Cursor, or another agent). Keep this Markdown
file in the repository as the source of truth.

## Copy-ready implementation prompt

You are working on the existing repository
`SoumyMittal/FresherRequirementSystem` (Sprout). Read the complete
`BATCH_RESUME_SCREENING_UPGRADE.md` specification before making any
changes. Treat it as the authoritative product and acceptance
specification.

### Your task

Implement the batch resume screening upgrade end to end in the existing
application.

The target user workflow is:

1.  HR selects a job opening.
2.  HR uploads multiple resumes.
3.  The system automatically extracts all resumes using the existing PDF
    text extraction, OCR, local parser, and optional Gemini integration.
4.  The system shows an extraction summary and identifies eligible
    records and records needing data review.
5.  HR clicks one button: **Run Model on All Resumes**.
6.  The backend validates and processes all eligible profiles through
    the existing shared recruitment pipeline in batch.
7.  The system generates the ML shortlist output, separate weighted
    recruitment score, and job-specific ranking.
8.  Model-shortlisted candidates are automatically routed to **HR
    Shortlist**.
9.  Valid non-shortlisted candidates remain in the general candidate
    pool.
10. Only invalid, out-of-bound, ambiguous, or unreliable extracted
    records go to **Need Data Review**.
11. HR corrections can be revalidated and assessed in a subsequent run.
12. Model runs never make final HR hiring decisions.

### Mandatory engineering constraints

-   First inspect the actual current code, routes, state model, frontend
    components, tests, model artifact, and preprocessing pipeline. Do
    not assume documentation perfectly matches code.
-   Reuse the existing `RecruitmentPipeline`, feature engineering,
    validation, model inference, resume extraction, Gemini integration,
    and persistence wherever appropriate.
-   Do not create a parallel implementation of feature engineering or
    scoring.
-   Do not remove existing functionality unrelated to this upgrade.
-   Preserve application IDs, job IDs, evidence, original resumes, and
    audit history.
-   Implement server-side validation; frontend validation is only for
    user experience.
-   Make batch processing resilient: one bad resume must not fail the
    rest.
-   Implement safe retry/idempotency and prevent duplicate shortlist
    entries.
-   Ensure batches are job-specific.
-   Preserve the separation between ML score, weighted recruitment
    score, rank, and HR decision.
-   Do not automatically reject candidates or change HR decisions.
-   Do not introduce SQLite or another database, perform migrations, or
    replace the saved model unless explicitly necessary and approved.
-   Do not expose API keys or sensitive candidate information in logs or
    frontend responses.
-   Do not claim a feature or test is complete unless it is implemented
    and verified.

### Missing-value requirements

The product specification requests zero for missing numerical
model-ready fields and `Not Provided` for missing text fields. Before
applying these values, inspect the saved model artifact's fitted
preprocessing pipeline and exact feature contract.

Keep raw extracted values, corrected values, normalized model-ready
values, and missingness/provenance metadata separate. Distinguish
missing values from genuine zero and explicit empty sections. Never
convert an out-of-bound or suspiciously extracted value into zero as a
way to bypass review.

If the requested defaults are incompatible with the fitted model, do not
silently feed incompatible values to it. Implement a documented
compatibility layer or explain why retraining/validation is required.
Preserve the existing model and its threshold unless an explicit,
evidence-backed change is approved.

### Need Data Review rules

Only route records to Need Data Review when the data is invalid, out of
bounds, contradictory, ambiguous, or unreliable enough that safe
assessment is not possible. Missing optional fields that can safely use
approved defaults should not force manual review. A missing required
field must be handled according to the model's validated compatibility
and eligibility rules, not guessed.

For each review item, show the affected field, extracted value, reason,
and source evidence/page when available. Preserve correction history.

### Required implementation process

**Phase 1 --- Repository audit** - Trace upload endpoints, extraction
queue, screening records, manual confirmation gate, CSV pipeline, model
inference, persistence, and frontend routing. - Identify the exact files
and functions that must change. - Check the saved artifact's expected
feature names, order, preprocessing, and threshold. - Report any
conflict between the specification and current implementation before
making risky changes.

**Phase 2 --- Backend** - Implement batch extraction orchestration or
adapt the existing queue. - Add explicit batch/job state and
per-document status. - Add batch inference using the shared pipeline. -
Add server-side validation and field-level review reasons. - Add
missing-value provenance and model-ready normalization. - Add duplicate
detection and safe retries. - Persist run metadata, outputs, routing,
and audit information. - Ensure partial failures do not block successful
records.

**Phase 3 --- Frontend** - Update Resume Studio to support the upload →
extract all → summary → one-click batch model flow. - Add the **Run
Model on All Resumes** action and accurate eligible/review counts. -
Populate HR Shortlist automatically from batch results. - Keep valid
non-shortlisted candidates in the general pool. - Restrict Need Data
Review to genuine validation/extraction exceptions. - Provide candidate
details, evidence, corrections, retry, and HR decision controls. - Keep
the UI responsive and accessible.

**Phase 4 --- Tests** Add or update tests for: - Multiple resume
extraction. - Text, scanned, and mixed PDFs. - One failed file while
others succeed. - Batch model execution with multiple valid profiles. -
Job-specific processing and ranking. - Missing numeric/text defaults and
provenance. - Genuine zero versus missing. - Out-of-bound and ambiguous
fields. - Need Data Review routing. - HR Shortlist and general-pool
routing. - Duplicate uploads and same-candidate applications. - Retry
and repeated batch-run idempotency. - HR decisions surviving model
reruns. - Model input feature order and preprocessing compatibility. -
Existing CSV, Gemini, OCR, workflow, and browser regressions.

**Phase 5 --- Verification and handoff** - Run the complete backend test
suite. - Run frontend syntax checks and all existing browser tests. -
Run new batch workflow tests. - Report exact commands and actual
pass/fail counts. - List changed files and explain each major change. -
Document any limitations or decisions requiring approval. - Provide
exact PowerShell commands to run the upgraded application.

### Definition of done

The work is done only when HR can upload a batch of resumes, allow all
extraction to finish, click one button to assess all eligible resumes,
and see the resulting candidates automatically distributed among HR
Shortlist, the general candidate pool, and Need Data Review according to
the rules in this specification.

Start with Phase 1. Do not immediately rewrite the application. Audit
the current implementation, then make the smallest coherent set of
changes that fully satisfies the specification.
