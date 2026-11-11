"""Example: .venv/Scripts/python.exe scripts/run_csv_pipeline.py --input input.csv --output scored.csv"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.pipeline import RecruitmentPipeline
from backend.pipeline.config import PipelineConfig
from backend.pipeline.pipeline import ValidationError


def main(argv=None):
    parser = argparse.ArgumentParser(description='Incepta standalone, deterministic CSV-to-ML pipeline')
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', default='Incepta_Scored_Applications_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.csv')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--strict', action='store_true', help='Default: stop if any row is invalid')
    mode.add_argument('--report', action='store_true', help='Score valid rows and write invalid rows to a report')
    parser.add_argument('--validation-report')
    parser.add_argument('--job-id')
    parser.add_argument('--recover-candidate-fields', action='store_true')
    parser.add_argument('--legacy-penalties', action='store_true', help='Explicitly enable historical CGPA (.70) and degree (.80) penalties')
    args = parser.parse_args(argv)
    try:
        pipeline = RecruitmentPipeline(PipelineConfig(legacy_penalties=args.legacy_penalties))
        result = pipeline.process_csv(args.input, args.output, strict=not args.report,
                                      validation_report=args.validation_report, job_id=args.job_id, recover=args.recover_candidate_fields)
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'Pipeline failed: {exc}', file=sys.stderr)
        if isinstance(exc, ValidationError):
            print('Validation errors: ' + json.dumps(exc.errors[:5]), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
