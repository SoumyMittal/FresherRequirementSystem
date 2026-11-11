import csv
import os
import tempfile
from pathlib import Path


def write_csv(path, records, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = list(dict.fromkeys(key for record in records for key in record))
    handle, temporary = tempfile.mkstemp(prefix='.incepta-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', newline='', encoding='utf-8-sig') as stream:
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(records)
        os.replace(temporary, path)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise
