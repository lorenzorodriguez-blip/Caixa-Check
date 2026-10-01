"""Run Caixa Check headlessly over a batch of per-client CSV+JSON pairs.

Usage:
    python scripts/batch_check.py <base_dir>

<base_dir> must contain one subfolder per client, each with:
    positions.csv
    report.json

Prints a JSON summary to stdout: per-client totals (pass/warn/fail) and the
detail of every non-passing check, plus a top-level list of client folder
names that have at least one 'fail'.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.calcs import build_calcs, extract_json
from src.checks import run_checks
from src.parser import parse_csv

STALE_PRICE_WIDGET = 'Antigüedad de precios de activos'
STALE_PRICE_RE = re.compile(
    r'^(?P<asset>.*?) \| ISIN: (?P<isin>\S+) \| precio: (?P<price_date>\d{2}/\d{2}/\d{4}) \| '
    r'(?P<days>\d+) día\(s\) \[(?P<tag>\w+)\]$'
)


def _parse_stale_prices(checks: list) -> list:
    rows = []
    for c in checks:
        if c['widget'] != STALE_PRICE_WIDGET:
            continue
        for line in c['detail']:
            m = STALE_PRICE_RE.match(line)
            if not m:
                rows.append({'raw': line})
                continue
            rows.append({
                'isin': m['isin'],
                'asset_description': m['asset'],
                'last_price_date': m['price_date'],
                'days_stale': int(m['days']),
                'severity': 'fail' if m['tag'] == 'ERROR' else 'warn',
            })
    return rows


def check_client(csv_path: Path, json_path: Path) -> dict:
    df = parse_csv(csv_path.read_text(encoding='utf-8'))
    calcs = build_calcs(df)
    jx = extract_json(json.loads(json_path.read_text(encoding='utf-8')))
    checks = run_checks(calcs, jx)

    n_fail = sum(1 for c in checks if c['status'] == 'fail')
    n_warn = sum(1 for c in checks if c['status'] == 'warn')
    n_pass = sum(1 for c in checks if c['status'] == 'pass')

    return {
        'total': len(checks),
        'pass': n_pass,
        'warn': n_warn,
        'fail': n_fail,
        'issues': [c for c in checks if c['status'] in ('fail', 'warn')],
        'stale_prices': _parse_stale_prices(checks),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')
    base = Path(sys.argv[1])
    results = {}
    for client_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        csv_path = client_dir / 'positions.csv'
        json_path = client_dir / 'report.json'
        if not (csv_path.exists() and json_path.exists()):
            results[client_dir.name] = {'error': 'missing positions.csv or report.json'}
            continue
        try:
            results[client_dir.name] = check_client(csv_path, json_path)
        except Exception as e:
            results[client_dir.name] = {'error': str(e)}

    problems = [
        name for name, r in results.items()
        if r.get('fail', 0) > 0 or 'error' in r
    ]

    stale_prices_all = [
        {**row, 'client': name}
        for name, r in results.items()
        for row in r.get('stale_prices', [])
    ]

    print(json.dumps({
        'clients': results,
        'clients_with_problems': problems,
        'stale_prices_all': stale_prices_all,
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
