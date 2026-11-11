# Incepta test pack

All names, contact details, education and achievements are fictional. Files are test fixtures only; nothing is automatically uploaded or inserted into application storage.

| Resume | Select this opening | Purpose |
| --- | --- | --- |
| `resumes/01_python_developer_text.pdf` | JOB_004 / Python Developer | Complete profile; ordinary embedded PDF text |
| `resumes/02_ml_engineer_scanned.pdf` | JOB_001 / AI/ML Engineer | Complete profile; image-only PDF that requires real OCR |
| `resumes/03_data_analyst_text.pdf` | JOB_002 / Data Analyst | Explicit empty internships/achievements and one backlog |
| `resumes/04_missing_academics_text.pdf` | JOB_003 / Software Engineer | Missing CGPA, school percentages and backlog count; prediction must remain blocked |
| `resumes/05_software_engineer_mixed.pdf` | JOB_003 / Software Engineer | Two pages: embedded text on page 1, image-only sections on page 2 |

Upload one PDF at a time in the existing Resume Studio. Inspect the extracted data and original PDF before confirmation. With a Gemini key, the text is structured by Gemini; without a key, the local parser remains available. OCR output can contain mistakes. No sample is labelled as guaranteed to pass the classifier threshold.

`applications_valid.csv` contains the four complete profiles in the exact raw 23-column contract. `applications_with_missing.csv` adds the deliberately incomplete profile. `expected_results.json` records the fictional ground truth for comparison; these are not predictions.

From the repository root:

```powershell
./.venv/Scripts/python.exe scripts/run_csv_pipeline.py --input samples/applications_valid.csv --output tmp/sample-scored.csv
./.venv/Scripts/python.exe scripts/run_csv_pipeline.py --input samples/applications_with_missing.csv --output tmp/sample-report.csv --report
```

The first command produces four scored rows. The second produces four valid rows and a validation-error report for the fifth. Strict mode is the default; omit `--report` to stop instead. Use new output names on subsequent runs; the CLI protects existing outputs.

To regenerate the fixtures, install `reportlab>=4,<5`, then run `scripts/create_sample_resumes.py`. Generated PDFs are intentionally simple and clearly labelled fictional so they are easy to inspect and parse.
