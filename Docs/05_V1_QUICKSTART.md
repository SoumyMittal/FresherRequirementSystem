# Sprout V1 — local prototype

The working app uses **AI_Fresher_Recruitment_ML_Dataset.csv** and the existing **fresher_recruitment_model.joblib**. Source CSVs and notebooks are unchanged.

## Start

Use Windows PowerShell in this repository:

```powershell
./start.ps1
```

Open **http://127.0.0.1:8000**. The first run creates `.venv` and installs dependencies if the environment does not exist. Python 3.12 and the Windows `py` launcher are required. For an existing environment with missing dependencies, run:

```powershell
./.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
```

No Node setup, frontend build, database, cloud account, or OCR executable is required. RapidOCR includes its English OCR models and uses the CPU. Interface fonts are fetched from Google Fonts when online; system fonts are the fallback.

## What works

- Demo login: any email and non-empty password. Credentials are never sent to the backend. This is a local, unauthenticated prototype; do not expose the server to a public network.
- Overview: live counts from 16,508 CSV application records plus local uploads.
- Talent pool: server-backed search, position/segment/review filters, pagination, application detail, HR decisions, and filtered CSV export.
- Run segmentation: score the selected position's CSV applications, or all CSV applications when no position is selected, using the saved model and its saved threshold. Uploaded resumes require individual confirmation and prediction.
- Open positions: create/edit jobs, change status, view the role's candidate pool. Existing CSV job rows stay unchanged; local job overrides apply to new model predictions.
- Resume studio: upload text, scanned, or mixed PDFs; extract embedded text and run OCR for pages with insufficient text. PDFs are limited to 10 MB and 15 pages. Unreadable or password-protected files show errors.
- Review: original PDF preview, OCR text/notes, editable candidate fields, explicit confirmation of empty sections, validation, and prediction only after complete confirmation.
- Reports: real dataset/workspace counts and model notes.

## Demonstration journey

1. Enter the demo workspace.
2. Open Talent pool and choose a position. Click Run segmentation to generate model groups from the ML CSV.
3. Open an application to inspect evidence and record a separate HR decision.
4. Open Resume studio, select an active position, and upload a PDF.
5. Wait for real extraction/OCR, then review the draft against the original.
6. Confirm degree, specialization, CGPA on a 10-point scale, Class 10/12 percentages, and backlog count. The existing model requires all of these fields. Unknown values cannot silently become zero.
7. Review lists, remove description lines treated as entries, and use “Confirm no …” only when no entries is correct.
8. Choose Confirm & run model. The result is Potential Match or Lower Model Match using the saved threshold (~0.8762); incomplete records remain Needs Data Review.
9. Record an HR decision. Prediction never changes it automatically.

## Storage and model behavior

No database is used or connected. Local job overrides, uploaded resume metadata, extraction data, confirmed inputs, upload predictions, and HR decisions are saved in `.runtime/state.json`; PDFs are in `.runtime/uploads`. Both are ignored by Git. Original CSV records are read-only. Dataset predictions are held in server memory and cleared when the server restarts; the interface labels them as session model runs. HR decisions persist.

The adapter reproduces the notebook's 34 input columns. Count normalization uses the fixed reference dataset maxima: projects 5, internships 4, certifications 5, achievements 4. It never derives maxima from an upload batch. The saved Logistic Regression pipeline was trained with scikit-learn 1.7.2; this version is pinned because 1.8 cannot load its preprocessing reliably.

Dataset Shortlist and Dataset Pool are original synthetic labels. They are distinct from new model segments. Dataset weighted scores and new model scores have separate labels. Model outputs are uncalibrated scores from synthetic shortlist training, not hiring probabilities. HR decisions remain separate from prediction segments. Editing confirmed data or job requirements invalidates uploaded model predictions.

Extraction is intentionally small: English OCR, heading-based list extraction, skills dictionary, and regular expressions. Complex columns, ambiguous sections, GPA scales, and school marks need human review. Grade values are not guessed. Existing dataset empty-list formatting is preserved in source files; newly confirmed empty lists use `None` at the model boundary.

## Checks

Backend checks use temporary files outside application storage:

```powershell
./.venv/Scripts/python.exe -m pip install -r backend/requirements-dev.txt
./.venv/Scripts/python.exe -m unittest discover -s tests -p test_workflow.py -v
```

For browser checks, keep the server running. Microsoft Edge must be installed:

```powershell
npm ci
npm run check
npm run test:ui
```

Browser checks create screenshots under ignored `test-results/` and exercise a Reviewed decision on an existing synthetic application, then restore its prior status. They do not create application dummy candidates or jobs. OCR test resumes exist only inside an isolated temporary test runtime.
