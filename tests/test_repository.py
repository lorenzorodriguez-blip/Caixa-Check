import pytest
from datetime import date
from src.repository import save_report, delete_report, list_reports


def test_delete_report_removes_json(tmp_path, monkeypatch):
    monkeypatch.setattr('src.repository.DATA_DIR', tmp_path)
    d = date(2026, 1, 15)
    save_report('client-1', d, {'x': 1})
    assert (tmp_path / 'client-1' / '2026-01-15.json').exists()
    delete_report('client-1', d)
    assert not (tmp_path / 'client-1' / '2026-01-15.json').exists()


def test_delete_report_removes_excel_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr('src.repository.DATA_DIR', tmp_path)
    d = date(2026, 1, 15)
    save_report('client-1', d, {'x': 1}, excel_bytes=b'fake-excel')
    assert (tmp_path / 'client-1' / '2026-01-15.xlsx').exists()
    delete_report('client-1', d)
    assert not (tmp_path / 'client-1' / '2026-01-15.xlsx').exists()


def test_delete_report_no_error_when_files_missing(tmp_path, monkeypatch):
    monkeypatch.setattr('src.repository.DATA_DIR', tmp_path)
    # Should not raise even if nothing was ever saved
    delete_report('client-1', date(2026, 1, 15))


def test_delete_report_removed_from_list(tmp_path, monkeypatch):
    monkeypatch.setattr('src.repository.DATA_DIR', tmp_path)
    d = date(2026, 1, 15)
    save_report('client-1', d, {'x': 1})
    delete_report('client-1', d)
    assert list_reports('client-1') == []
