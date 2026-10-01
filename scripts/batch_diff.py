"""Archive tramoia reports into data/reports/<client>/<date>.json and diff
each against the previous stored period for that client.

Usage:
    python scripts/batch_diff.py <base_dir>

<base_dir> must contain one subfolder per client, each with a report.json
(the raw tramoia JSON payload — no CSV needed, diffing is JSON-only).

For every client:
  - the report's own internal date (same extraction src/checks.py uses) is
    used as the archive filename, so it lines up with dates saved manually
    via the Streamlit app's "Repositorio" tab
  - the report is archived via src.repository.save_report (idempotent —
    overwrites that date's file if it already existed)
  - if an earlier archived date exists for that client, run_diff +
    run_asset_diff compare it against the new report

Prints a JSON summary to stdout.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.checks import _report_date
from src.diff import run_asset_diff, run_diff
from src.repository import get_previous_report, save_report


def severity_counts(diffs: list) -> dict:
    counts = {"big": 0, "medium": 0, "small": 0}
    for d in diffs:
        counts[d["sev"]] += 1
    return counts


def process_client(client_dir: Path) -> dict:
    json_path = client_dir / "report.json"
    if not json_path.exists():
        return {"error": "missing report.json"}

    report_data = json.loads(json_path.read_text(encoding="utf-8"))
    report_date = _report_date(report_data)
    if report_date is None:
        return {"error": "could not determine report date from JSON"}

    prev = get_previous_report(client_dir.name, report_date)
    save_report(client_dir.name, report_date, report_data)

    if prev is None:
        return {"report_date": report_date.isoformat(), "previous_date": None}

    prev_date, prev_data = prev
    metric_diffs = run_diff(prev_data, report_data)
    asset_diffs = run_asset_diff(prev_data, report_data)

    new_assets = [d for d in asset_diffs if d["status"] == "new"]
    removed_assets = [d for d in asset_diffs if d["status"] == "removed"]
    changed_assets = [d for d in asset_diffs if d["status"] == "changed"]

    return {
        "report_date": report_date.isoformat(),
        "previous_date": prev_date.isoformat(),
        "metric_diffs": metric_diffs,
        "metric_severity": severity_counts(metric_diffs),
        "asset_new": new_assets,
        "asset_removed": removed_assets,
        "asset_changed": changed_assets,
        "asset_severity": severity_counts(asset_diffs),
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(sys.argv[1])
    results = {}
    for client_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        try:
            results[client_dir.name] = process_client(client_dir)
        except Exception as e:
            results[client_dir.name] = {"error": str(e)}

    no_previous = [c for c, r in results.items() if r.get("previous_date") is None and "error" not in r]
    errored = [c for c, r in results.items() if "error" in r]
    big_moves = [
        c for c, r in results.items()
        if r.get("metric_severity", {}).get("big", 0) > 0
        or r.get("asset_severity", {}).get("big", 0) > 0
    ]

    print(json.dumps({
        "clients": results,
        "no_previous_period": no_previous,
        "errored": errored,
        "clients_with_big_moves": big_moves,
    }, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
