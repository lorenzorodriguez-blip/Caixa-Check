from datetime import date

from src.checks import _parse_ddmmyyyy


def test_parse_ddmmyyyy_valid():
    assert _parse_ddmmyyyy('24/07/2026') == date(2026, 7, 24)


def test_parse_ddmmyyyy_invalid_format():
    assert _parse_ddmmyyyy('2026-07-24') is None


def test_parse_ddmmyyyy_blank():
    assert _parse_ddmmyyyy('') is None


def test_parse_ddmmyyyy_none():
    assert _parse_ddmmyyyy(None) is None
