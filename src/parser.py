import ast
import io
import json

import pandas as pd


def parse_csv(file_content: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(file_content), dtype=str)
    df = df.fillna('')
    return df


def safe_parse(val) -> dict:
    """Parse a stringified dict (JS or JSON format) from a CSV field."""
    if not val or str(val).strip() in ('', 'nan', '{}', 'None', 'null'):
        return {}
    val = str(val).strip()
    try:
        return json.loads(val)
    except Exception:
        pass
    try:
        return json.loads(val.replace("'", '"'))
    except Exception:
        pass
    try:
        return ast.literal_eval(val)
    except Exception:
        pass
    return {}
