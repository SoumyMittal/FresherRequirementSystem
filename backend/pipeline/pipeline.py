from __future__ import annotations

import csv
from pathlib import Path

from .config import FEATURE_VERSION, SCORE_VERSION, PipelineConfig
from .schema import DERIVED_COLUMNS, RAW_COLUMNS, header_errors, verify_reference
from .validation import validate_records
from .missing_values import recover_candidate_fields
from .feature_engineering import make_features
from .recruitment_scoring import recruitment_score
from .model_inference import load_artifact, validate_artifact, infer
from .ranking import rank_records
from .csv_export import write_csv

RESULT_COLUMNS = (*DERIVED_COLUMNS, 'Recruitment_Score', 'Model_Score', 'Model_Prediction', 'Model_Segment',
                  'Model_Threshold', 'Model_Name', 'Model_Version', 'Model_Target', 'Feature_Schema_Version',
                  'Score_Formula_Version', 'Model_Rank', 'Recruitment_Rank', 'Processing_Status', 'Processing_Warnings')
ERROR_COLUMNS = ['Source_Row', 'Application ID', 'Candidate ID', 'Job ID', 'Errors']


class ValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f'{len(errors)} invalid row(s). See the validation report; no scored output was written.')


class RecruitmentPipeline:
    def __init__(self, config=None, artifact=None, model_version=None):
        self.config = config or PipelineConfig()
        verify_reference(self.config.reference_path)
        if artifact is None:
            self.artifact, self.model_version = load_artifact(self.config.model_path)
        else:
            self.artifact = validate_artifact(artifact)
            self.model_version = model_version or 'existing-loaded-artifact'

    def process_records(self, records, strict=True, recover=False):
        originals = [dict(r) for r in records]
        prepared = [dict(r, Source_Row=r.get('Source_Row', index + 2)) for index, r in enumerate(records)]
        if recover:
            prepared = recover_candidate_fields(prepared)
        valid, errors = validate_records(prepared)
        if strict and errors:
            raise ValidationError(errors)
        features = [make_features(r) for r in valid]
        probabilities = infer(features, self.artifact)
        original_by_id = {r.get('Application ID'): r for r in originals}
        output = []
        for row, probability in zip(features, probabilities):
            source = original_by_id[row['Application ID']]
            result = dict(row)
            # Preserve every colliding original value under an explicit Input_ column.
            for key in (*RESULT_COLUMNS, *RAW_COLUMNS):
                if key in source:
                    if key in RAW_COLUMNS and source[key] == row.get(key):
                        continue
                    if key in RAW_COLUMNS and not recover:
                        continue
                    backup = 'Input_' + key
                    if backup in source:
                        raise ValueError(f'Input column {backup} conflicts with the audit backup for {key}.')
                    result[backup] = source[key]
            result.update(Recruitment_Score=recruitment_score(row, self.config.legacy_penalties), Model_Score=probability,
                          Model_Prediction=int(probability >= float(self.artifact['threshold'])),
                          Model_Segment='Potential Match' if probability >= float(self.artifact['threshold']) else 'Lower Model Match',
                          Model_Threshold=float(self.artifact['threshold']), Model_Name=self.artifact['model_name'],
                          Model_Version=self.model_version, Model_Target=self.artifact['target'],
                          Feature_Schema_Version=FEATURE_VERSION,
                          Score_Formula_Version=SCORE_VERSION + ('-legacy-penalties' if self.config.legacy_penalties else ''),
                          Processing_Status='completed', Processing_Warnings=row.get('Processing_Warnings', ''))
            output.append(result)
        return rank_records(output), errors

    def process_csv(self, input_path, output_path, strict=True, validation_report=None, job_id=None, recover=False):
        input_path, output_path = Path(input_path).resolve(), Path(output_path).resolve()
        report_path = Path(validation_report).resolve() if validation_report else output_path.with_name(output_path.stem + '_Validation_Errors.csv')
        if input_path.suffix.lower() != '.csv':
            raise ValueError('Input must be a .csv file.')
        if len({input_path, output_path, report_path}) != 3:
            raise ValueError('Input, output, and validation report paths must all be different.')
        if output_path.exists() or report_path.exists():
            raise ValueError('Output/report already exists. Choose new paths to preserve prior results.')
        with input_path.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            errors = header_errors(reader.fieldnames)
            if errors:
                raise ValueError('; '.join(errors))
            records = []
            for index, row in enumerate(reader):
                if None in row:
                    raise ValueError(f'CSV record {index + 2} has extra cells. Quote text containing commas.')
                if 'Source_Row' in row:
                    raise ValueError('Source_Row is reserved for input record identity.')
                row['Source_Row'] = index + 2
                records.append(row)
        # Validate the complete input before optional job filtering so invalid rows are never hidden.
        try:
            scored, errors = self.process_records(records, strict=strict, recover=recover)
        except ValidationError as exc:
            write_csv(report_path, exc.errors, ERROR_COLUMNS)
            raise
        if job_id:
            scored = [r for r in scored if r['Job ID'] == job_id]
        if errors:
            write_csv(report_path, errors, ERROR_COLUMNS)
        columns = list(dict.fromkeys([*RAW_COLUMNS, *(key for row in scored for key in row), *RESULT_COLUMNS, 'Source_Row']))
        write_csv(output_path, scored, columns)
        return {'input': str(input_path), 'total_rows': len(records), 'valid_rows': len(records) - len(errors),
                'invalid_rows': len(errors), 'output_rows': len(scored), 'unique_candidates': len({r['Candidate ID'] for r in scored}),
                'jobs_represented': len({r['Job ID'] for r in scored}), 'model': self.artifact['model_name'],
                'threshold': float(self.artifact['threshold']), 'successful_predictions': len(scored), 'output': str(output_path),
                'validation_report': str(report_path) if errors else None}
