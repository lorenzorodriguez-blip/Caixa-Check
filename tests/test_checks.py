from datetime import date

from src.checks import _parse_ddmmyyyy
from src.checks import _report_date


def test_parse_ddmmyyyy_valid():
    assert _parse_ddmmyyyy('24/07/2026') == date(2026, 7, 24)


def test_parse_ddmmyyyy_invalid_format():
    assert _parse_ddmmyyyy('2026-07-24') is None


def test_parse_ddmmyyyy_blank():
    assert _parse_ddmmyyyy('') is None


def test_parse_ddmmyyyy_none():
    assert _parse_ddmmyyyy(None) is None


def test_report_date_found():
    jx = {'pages': [
        {'widgets': []},
        {'widgets': [
            {'content': [{'data': {'value': 100, 'count': 1, 'date': '24/07/2026'}}]},
        ]},
    ]}
    assert _report_date(jx) == date(2026, 7, 24)


def test_report_date_missing():
    jx = {'pages': [
        {'widgets': [{'content': [{'data': {'value': 100}}]}]},
    ]}
    assert _report_date(jx) is None


def test_report_date_no_pages():
    assert _report_date({'pages': []}) is None


def test_report_date_ignores_non_dict_data():
    jx = {'pages': [
        {'widgets': [{'content': [{'data': [1, 2, 3]}]}]},
    ]}
    assert _report_date(jx) is None
