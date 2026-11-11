# Sprout · AI Fresher Recruitment V1

A local recruitment prototype with a polished HR workspace, mocked login, real resume extraction/OCR, confirmed candidate data, and saved-model segmentation.

Uses **AI_Fresher_Recruitment_ML_Dataset.csv** and **fresher_recruitment_model.joblib**. No database is used. Original datasets are unchanged.

```powershell
./start.ps1
```

Open **http://127.0.0.1:8000** and enter the demo workspace with any email/password. Python 3.12 is required; first-run setup installs Python dependencies. The app does not require Node or a frontend build to run.

**Flow:** select a position → upload PDF → extract text / OCR → review and confirm data → predict segment → record an HR decision.

The talent pool supports search, filters, batch segmentation of CSV applications, and export. Open positions support creation and editing. Uploaded resumes, local edits, and HR decisions persist in ignored `.runtime` files. This is a local prototype with mocked authentication, not a public deployment.

See [V1 quickstart](Docs/05_V1_QUICKSTART.md) for details, model limitations, and verification commands. The earlier [implementation plan](Docs/04_IMPLEMENTATION_PLAN.md) documents the overall approach; V1 uses the ML CSV as requested.

The [Incepta checkpoint](Docs/06_INCEPTA_CHECKPOINT.md) adds a standalone CSV-to-CSV pipeline, optional Gemini resume parsing, and a [fictional resume test pack](samples/README.md). Put your key in the ignored root `.env` (`GEMINI_API_KEY=...`) and restart the app to enable Gemini; local parsing still works without a key.
