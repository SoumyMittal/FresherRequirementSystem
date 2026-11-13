# Sprout Â· AI Fresher Recruitment V1

A local recruitment prototype with mocked login, PDF and OCR extraction, job-specific batch screening, and HR decisions.

Uses **AI_Fresher_Recruitment_ML_Dataset.csv** and **fresher_recruitment_model.joblib**. No database is used. Original datasets are unchanged.

```powershell
./start.ps1
```

Open **http://127.0.0.1:8000** and enter the demo workspace with any email/password. Python 3.12 is required; first-run setup installs Python dependencies. The app does not require Node or a frontend build to run.

Select an active position in **Resume studio**, choose one or more PDFs, and start extraction. Once the summary is ready, select **Run Model on All Resumes**. The talent pool has views for **HR Shortlist**, non-shortlisted applicants, **Need Data Review**, and applications awaiting assessment. Correct and revalidate affected profiles from their detail view, then return to the original batch to assess them. Resume Studio retains batch history across refreshes.

The talent pool also supports search, filters, CSV segmentation, and export. Open positions support creation and editing. Resume PDFs, extracted text, decisions, and run history persist in ignored `.runtime` files. Run one local server process. Demo login does not authenticate users or identify decision makers. Keep the server on loopback and restrict access to the runtime folder. Retention and deletion are managed by the local operator under their candidate-data policy. Gemini is optional and sends extracted resume text to Google when enabled.

Batch limits default to 30 files, 15 MB per file, 50 pages per file, and two concurrent extraction slots across batches. Override these values with the process environment settings in `.env.example` before startup.

Each position has a shortlisting ratio, defaulting to 3.5 candidates per opening. The server rounds openings × ratio upward. One capacity applies across the position's assessed resume batches. The saved threshold determines which candidates qualify, and the ML score, weighted recruitment score, and application ID determine placement. Edit the position and rerun a batch to activate a changed capacity. Earlier runs retain their original summaries. The job detail shows the current allocation and the configuration that produced it.

The batch profile records zero and `Not Provided` for absent inputs alongside original facts, HR corrections, and provenance. For inference, `reference-fallbacks-v1` preserves the existing Notebook 03 reference medians, specialization mode, and text markers. The saved classifier uses a median imputer and StandardScaler for numeric columns, and a most-frequent imputer and unknown-tolerant one-hot encoder for categorical columns. The adapter preserves legacy predictions on the 100 masked synthetic fixtures in the compatibility regression. Feeding the requested defaults directly produced 13 threshold crossings in that same sample. The job's separate CGPA check returns unknown for an absent grade.

See the [batch screening specification](BATCH_RESUME_SCREENING_UPGRADE.md) for the product and acceptance requirements.

See [V1 quickstart](Docs/05_V1_QUICKSTART.md) for details, model limitations, and verification commands. The earlier [implementation plan](Docs/04_IMPLEMENTATION_PLAN.md) documents the overall approach; V1 uses the ML CSV as requested.

The [Incepta checkpoint](Docs/06_INCEPTA_CHECKPOINT.md) adds a standalone CSV-to-CSV pipeline, optional Gemini resume parsing, and a [fictional resume test pack](samples/README.md). Put your key in the ignored root `.env` (`GEMINI_API_KEY=...`) and restart the app to enable Gemini; local parsing still works without a key.
