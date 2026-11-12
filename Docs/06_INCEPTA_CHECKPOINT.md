# Incepta checkpoint: shared CSV pipeline + optional Gemini parsing

## Scope

The supplied implementation plan's immediate task is Phase 1 only. This checkpoint completes the standalone CSV-to-CSV pipeline and reuses it in existing app prediction routes. The user's explicit additional request authorizes optional Gemini parsing and sample resumes. It does not implement the later DOCX/multi-document ingestion, UI redesign/top-10 view, JEV/relevance evaluation, or SQLite migration. Existing single-PDF OCR and mocked login remain available. No database connection, schema, migration, or application data seeding is performed.

## Run the app and configure Gemini

Python 3.12:

```powershell
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
./start.ps1
```

A blank `.env` has been created in the repository root without replacing an existing file. Set:

```dotenv
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-flash-latest
GEMINI_TIMEOUT_SECONDS=30
```

Restart the app after editing `.env`. Existing process environment variables take precedence. `.env` is ignored by Git; `.env.example` contains no secrets. The key is read by Python only and sent as the `X-goog-api-key` header to Google's fixed `generateContent` REST endpoint. The frontend and health response never receive it. No Google SDK or database setup is required.

With no key, normal local parsing continues. With a key, extracted PDF/OCR text is sent to Gemini for schema-constrained extraction. The upload view identifies that behavior. Gemini produces field values, grouped entries, and quoted source evidence, not recruitment scores or candidate-quality judgments. Values without supporting evidence are left unknown. HR must still review the PDF and confirm every mandatory model input. API failures, malformed output, timeout, or quota errors produce a visible extraction warning and fall back to the local parser. Live Gemini connectivity has not been verified without a supplied key; mocked request/response/error tests verify the integration.

References checked: [Google generateContent REST API](https://ai.google.dev/api/generate-content) and [structured JSON output](https://ai.google.dev/gemini-api/docs/structured-output). The requested `gemini-flash-latest` alias is used as-is; model availability depends on the API account.

## Standalone CLI

This requires neither FastAPI nor OCR nor Gemini. It never retrains the model.

```powershell
./.venv/Scripts/python.exe scripts/run_csv_pipeline.py --input AI_Fresher_Recruitment_ML_Dataset.csv --output Incepta_Scored_Applications.csv
```

The output from the verified full run contains 16,508 applications, 10,000 unique candidate IDs, and four job IDs, with zero invalid rows. The pipeline also accepts raw 23-column CSVs, including the four complete sample profiles in `samples/applications_valid.csv`.

Default strict mode stops on invalid records, writes a validation-error CSV, leaves the input unchanged, and returns a nonzero exit code. `--report` processes valid rows and separately lists every invalid record and reason. Header errors are reported directly and do not produce an invalid output CSV. `--validation-report PATH` chooses the report path; otherwise it is derived from the output name. Existing output/report paths are rejected, not silently overwritten. Missing numeric values remain unknown. Optional `--recover-candidate-fields` recovers only unambiguous same-candidate values, never batch medians/modes; conflicting values are not recovered. `--job-id` filters output after complete-input validation so invalid rows cannot be hidden by a filter.

## Shared implementation

- `backend/pipeline/config.py`: central model/reference paths, versioned constants and scoring options.
- `schema.py`, `validation.py`, `missing_values.py`: exact 23-column raw contract and validation/recovery.
- `feature_engineering.py`: the only implementation of the 14 derived feature definitions.
- `recruitment_scoring.py`: deterministic weighted score, with no synthetic noise.
- `model_inference.py`: validates artifact metadata/positive class, passes exact saved feature order, checks finite 0–1 outputs.
- `ranking.py`: independent per-job model/recruitment ranks; application ID breaks ties deterministically.
- `csv_export.py`, `pipeline.py`: standalone orchestration and atomic CSV writing.
- `scripts/run_csv_pipeline.py`: CLI, printed run summary, and failure exit status.
- `backend/gemini_parser.py`: optional text-to-structured-data parsing, isolated from model scoring.

The existing backend imports the shared feature function and uses `RecruitmentPipeline.process_records` for both confirmed resume predictions and CSV-reference batch predictions. The uploaded original, extracted text, evidence, parser identity, and saved pipeline output remain linked to the screening ID. Existing `.runtime` JSON/file storage is retained.

## Output and parity

Model inputs are selected from the saved artifact's `feature_columns`; identity, historical labels/ranks and weighted scores never enter inference. The 34-feature contract is checked by name against the versioned raw/derived schema, not guessed from a count.

Fixed training reference maxima are projects 5, internships 4, certifications 5, achievements 4. No incoming batch changes them. Model version is a SHA-256 prefix of the existing unchanged artifact. Each output includes feature-schema/score versions, model name/target/threshold, model score/class/segment, deterministic recruitment score, processing status, source record number and two per-job ranks. `Source_Row` is the logical CSV record number (header = 1), not a physical line number when quoted cells span lines. No top-10 truncation or automatic HR decision is applied.

Where input columns already contain generated fields, their original values are copied to explicit `Input_<column>` audit columns before the new values are written. This includes `Input_Recruitment_Score`; source CSV bytes remain unchanged. Existing historical `Rank`, `Shortlist Limit`, and `Shortlisted` stay as historical input columns and are not new threshold decisions. Recovered raw fields also keep input backups. Output audit-column name conflicts are rejected.

Full-reference parity checks compare every generated feature and model score to the current reference/model path. They agree within numeric tolerance. Weighted recruitment scores intentionally differ from historical `Recruitment_Score`: live inference removes Gaussian noise and, by default, the historical CGPA/degree penalties. Use `--legacy-penalties` to deliberately retain the .70 CGPA and .80 degree multipliers; its score-version label differs. The original score equation is otherwise unchanged, including allowing counts above training maxima and the historical backlog formula. Scores are not silently clamped. Model outputs remain uncalibrated synthetic-shortlist suggestions.

## Samples and verification

Five fictional PDFs in `samples/resumes/` cover text extraction, scanned OCR, explicit empty sections, missing academics, and mixed text/scanned pages. `samples/README.md` identifies the matching opening and expected behavior. Companion CSVs and expected JSON let you compare source facts without guessing outcomes. Fixtures are generated as files only and are never inserted into application storage.

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py" -v
node --check frontend/app.js
```

Backend tests isolate runtime files in temporary directories and disable real Gemini calls. Gemini tests mock the requested REST request, successful extraction, missing-key behavior, invalid responses, unsupported values, and API errors. The original integration tests continue checking actual OCR, confirmation-before-prediction, file rejection, persistence and feature parity. PDF sample layouts are rendered and visually inspected.

The desktop/mobile browser suite and `tests/browser_checkpoint.mjs` also verify the existing interface and a complete sample-PDF upload → extracted-field review → confirmation → shared-pipeline prediction. These were run against an isolated temporary runtime on port 8002, preserving application storage.

Final verification: 24 backend tests passed, both browser suites passed, and the full-reference CLI produced 16,508 scored rows with zero invalid records. Sample report mode produced four valid rows plus one invalid-row report. No original CSV, notebook, or saved model was modified.

Later phases have not been started. Before a future SQLite setup or migration, the exact proposed connection and schema changes must be presented for user approval under the project instructions.

## Follow-up: multiple PDFs and visible model mapping

Resume Studio now accepts up to ten PDFs per selection, supports adding/removing files before upload, and shows a per-document extraction queue. Each PDF is submitted to the existing validated screening endpoint and receives its own application ID, real backend status, review action, and error/retry action. Two extraction slots bound heavy processing; one failure does not block the others. The selected job is captured with each upload. Queue entries remain while navigating within the page; persisted application records remain accessible through history after reload. Retry creates a new screening record and preserves the failed attempt for traceability.

The review fields stay aligned with the model contract. Project/internship/certification/achievement counts update from the confirmed lists. Selected-job requirements are shown separately. “Check model inputs” validates the current unsaved form on the backend and displays the exact saved-artifact feature names, order and values. It neither confirms nor scores the resume. Missing fields still block prediction. Name/email are profile fields, not ML inputs. Confirmation and prediction use the same raw-record mapping and shared feature engine. A regression test captures the DataFrame actually passed to `predict_proba` and compares it with the preview, including the updated CGPA-derived features.

Verification for this follow-up: all 25 backend tests pass. Browser checks pass for selecting/adding multiple files, independent review/prediction of two resumes, an invalid third file not blocking the others, input-preview validation, and mobile layout. The existing desktop/mobile navigation suite also passes. Restart the Python server after updating to load the new input-preview endpoint, then refresh the browser.

## Follow-up: processing workshop and downloadable pipeline input

The plain queue is replaced with a full-width processing workshop: animated bloom, a current-action heading, page information, per-document state, and a handoff panel. Gathering, reading/OCR, structuring, Gemini grouping, and field-checking labels map to real backend work; they do not rotate on a fake success timer. The batch meter counts finished files (successful or failed), while extraction/confirmation/error counts remain separate. Backend extraction history and page totals are retained. CSS/JavaScript asset URLs are versioned to prevent an old cached stylesheet from leaving the new screen unstyled. Reduced-motion preferences are respected.

After extraction, **Download extracted draft** exports finished documents with unknown values left blank. It is explicitly not guaranteed ready for inference. **Download ML input CSV** exports only complete, HR-confirmed documents, validated again on the server. The displayed count is the exact number of profiles included; unfinished/failed/unconfirmed records are not silently included. Confirmed profiles also have a per-application CSV download available from their detail dialog/history.

The new `POST /api/screenings/export-csv` accepts `screening_ids` and `mode` (`model` or `draft`). It exports exactly the shared 23-column raw application schema, including application/candidate/job IDs, confirmed list counts and selected-job requirements. No scores, predictions, synthetic targets, name or email columns are added. CSV quoting and UTF-8 BOM are handled by the server. Duplicate IDs, nonexistent/unfinished records and unconfirmed model-ready exports are rejected. Draft unknown counts stay blank rather than becoming zero.

Run a downloaded model-ready CSV through the shared implementation of notebook stages 03–06:

```powershell
./.venv/Scripts/python.exe scripts/run_csv_pipeline.py --input path/to/Incepta_Applications.csv --output path/to/Incepta_Scored.csv
```

This validates missing values, generates the frozen/versioned features, and uses the existing fitted model. It does not rerun EDA, training splits, retraining or historical synthetic-data imputation/noise for an upload. Existing notebooks and original datasets remain unchanged. Choose a new output name for repeat runs.

Verification: all 26 backend tests passed. Browser checks cover the active processing screen, multi-file failure isolation, draft/model-ready downloads, confirmation gating and mobile rendering. The exact CSV downloaded in the browser was passed to the standalone CLI: two applications, zero invalid rows, two successful predictions. No production runtime data was used for these checks.

## Follow-up: scores that appeared as zero

The reported application had a genuine classifier output near `5.47e-11`, displayed as `0.0%` by one-decimal rounding, while its separate weighted recruitment score was already `55.45/100`. The UI now shows the weighted recruitment score prominently and the ML shortlist signal as a separate measure. Very small positive classifier outputs use additional precision or scientific notation. True zero remains zero; model outputs, weights, threshold and segments are unchanged.

Candidate lists and summary exports retain recruitment and classifier scores separately. Dataset predictions cache their newly computed weighted score alongside their classifier output, rather than confusing it with the historical noisy dataset score. Invalidated uploads do not show a stale recruitment score. This does not recalibrate/retrain the synthetic shortlist model or promise that example resumes meet its threshold.

All 27 backend tests pass, including preservation of a tiny nonzero classifier output, a separate positive recruitment score, and clearing displayed scores after data changes. The browser regression verifies that uploaded profiles show a recruitment score independently of the model signal.

## Incepta: section grouping, optional fields and validation

The application now uses the Incepta name. `backend/resume_sections.py` recognizes section aliases (Projects, Academic Projects, Experience, Work Experience, Internship Experience, Awards/Achievements, and Certifications). Entries retain a title, description, source text, source line and section. Description/action bullets and date/company continuation lines attach to the preceding entry instead of inflating counts. Intern/trainee roles found under Experience populate Internships; other employment is retained separately in the evidence/review view and is not falsely counted as an internship. Ambiguous layouts still need review; Gemini parsing remains optional, with local evidence preserved when Gemini omits a locally found field.

School percentages support Class X/XII, 10th/12th, SSC/SSLC/HSC and common higher-secondary labels with intervening school/board/year text. An explicitly stated “no active backlogs” is zero; absent backlog information is unknown. Counts are generated from grouped entry lists, never description-line counts. Unknown sections remain null; explicit declarations of no entries remain empty lists.

Blank review fields display **Not provided** and are no longer HTML-required. “Confirm no entries” controls were removed. Save review accepts incomplete records without guessing values. The separate validation layer reports missing/invalid model fields; only validated records can enter model inference or the model-ready CSV. Draft CSVs remain available with blank unknown values. Saving a review does not assert that it is model-ready. No historical training medians/modes or artificial zeros are applied to live profiles.

Removed the application's fixed upload size, PDF page, selected-file count, export row count and Gemini text-length caps. PDF format/readability checks remain. Actual machine memory, OCR speed and external-provider context/time limits still apply; processing concurrency remains bounded to protect responsiveness. Documents are not truncated to satisfy an arbitrary character/page count.

Verification: 33 backend tests pass, including grouped descriptions, experience aliases, long titles/many projects, incomplete saves with strict model admission, and 17-page extraction. Desktop/mobile browser suites pass, including no empty-section controls, Not provided placeholders, incomplete saves, validation-disabled inference and selecting 12 files. Tests use isolated runtime storage, not application records. No database changes or original notebook/model edits are part of this update.


### Latest preview and CSV handoff

The resume screen is now a read-only preview with empty missing fields, no confirmation controls and a Run model button. Before model CSV creation and inference, notebook 03 style handling is applied on a copy: numeric reference medians (integer counts rounded), reference specialization mode, and Not Provided for missing text. Extracted evidence and draft CSV blanks remain unchanged. The preview lists the filled fields and their methods. Invalid known values still fail validation. Model exports no longer require a separate confirmation step. The trained artifact and reference dataset are unchanged.

Verification for this final behavior: 33 backend regression tests plus two missing-value preparation tests passed; JavaScript syntax checks passed. Browser checkpoint assertions were updated for the read-only preview and automatic preparation.
