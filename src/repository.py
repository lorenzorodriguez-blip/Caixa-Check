import json
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "reports"
CLIENTS_FILE = Path(__file__).parent.parent / "data" / "clients.json"

_DEFAULT_CLIENTS = [
    "4c3f1e76-ff37-5f98-8564-9cf4eab4dfa1",
    "6da9a5d6-af17-54d3-a45e-785082c8d926",
    "7f327133-b6b5-5c83-af86-f409bb6a8fa7",
    "014647c8-4468-5569-abf6-63b1f65c9017",
    "ab9db297-fe2d-5659-8187-63e1926f5d60",
    "b754c55b-fc01-50dd-acd5-f836fb23698c",
    "ced538e6-9aa1-52eb-a406-19d7d95ad90c",
    "f43aaca0-0cfd-5a0f-a6a2-777cfa70dc36",
    "fdfbb548-0efd-5935-a145-72e6042bed6d",
]


def load_clients() -> list[str]:
    if not CLIENTS_FILE.exists():
        CLIENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CLIENTS_FILE.write_text(json.dumps(_DEFAULT_CLIENTS, indent=2), encoding="utf-8")
        return list(_DEFAULT_CLIENTS)
    return json.loads(CLIENTS_FILE.read_text(encoding="utf-8"))


def add_client(client_id: str) -> bool:
    """Add a client. Returns False if it already exists, True if added."""
    clients = load_clients()
    if client_id in clients:
        return False
    clients.append(client_id)
    CLIENTS_FILE.write_text(json.dumps(clients, indent=2), encoding="utf-8")
    return True


def _client_dir(client_id: str) -> Path:
    return DATA_DIR / client_id


def save_report(client_id: str, report_date: date, json_data: dict, excel_bytes: bytes | None = None) -> None:
    d = _client_dir(client_id)
    d.mkdir(parents=True, exist_ok=True)
    date_str = report_date.strftime("%Y-%m-%d")
    (d / f"{date_str}.json").write_text(json.dumps(json_data, ensure_ascii=False), encoding="utf-8")
    if excel_bytes:
        (d / f"{date_str}.xlsx").write_bytes(excel_bytes)


def list_reports(client_id: str) -> list[date]:
    d = _client_dir(client_id)
    if not d.exists():
        return []
    dates = []
    for f in d.glob("*.json"):
        try:
            dates.append(datetime.strptime(f.stem, "%Y-%m-%d").date())
        except ValueError:
            pass
    return sorted(dates)


def load_report(client_id: str, report_date: date) -> dict | None:
    path = _client_dir(client_id) / f"{report_date.strftime('%Y-%m-%d')}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_previous_report(client_id: str, current_date: date) -> tuple[date, dict] | None:
    dates = list_reports(client_id)
    previous = [d for d in dates if d < current_date]
    if not previous:
        return None
    prev_date = previous[-1]
    data = load_report(client_id, prev_date)
    return (prev_date, data) if data else None


def list_all_reports() -> list[dict]:
    rows = []
    for client_id in load_clients():
        for report_date in list_reports(client_id):
            xlsx_exists = (_client_dir(client_id) / f"{report_date.strftime('%Y-%m-%d')}.xlsx").exists()
            rows.append({
                "cliente": client_id,
                "fecha":   report_date.strftime("%Y-%m-%d"),
                "excel":   "si" if xlsx_exists else "no",
            })
    return sorted(rows, key=lambda r: (r["cliente"], r["fecha"]), reverse=True)
