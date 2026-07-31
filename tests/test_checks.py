from datetime import date

import pandas as pd

from src.checks import _parse_date
from src.checks import _report_date
from src.checks import _check_price_freshness
from src.checks import run_checks


def test_parse_date_valid_ddmmyyyy():
    assert _parse_date('24/07/2026') == date(2026, 7, 24)


def test_parse_date_invalid_format():
    assert _parse_date('not-a-date') is None


def test_parse_date_blank():
    assert _parse_date('') is None


def test_parse_date_none():
    assert _parse_date(None) is None


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


def _calcs(rows):
    return {'active': pd.DataFrame(rows)}


def test_price_freshness_all_fresh_returns_none():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '22/07/2026', 'final_market_value': 100.0},
    ])
    assert _check_price_freshness(calcs, date(2026, 7, 24)) is None


def test_price_freshness_exactly_3_days_is_ok():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '21/07/2026', 'final_market_value': 100.0},
    ])
    assert _check_price_freshness(calcs, date(2026, 7, 24)) is None


def test_price_freshness_4_days_is_warn():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '20/07/2026', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result['status'] == 'warn'
    assert len(result['detail']) == 1
    assert 'Fondo A' in result['detail'][0]
    assert 'LU0001' in result['detail'][0]


def test_price_freshness_detail_formats_iso_datetime_cleanly():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '2026-07-01T06:00:25.364000', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result is not None
    assert 'precio: 01/07/2026' in result['detail'][0]
    assert '06:00:25' not in result['detail'][0]
    assert '2026-07-01T' not in result['detail'][0]


def test_price_freshness_7_days_is_warn():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '17/07/2026', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result['status'] == 'warn'


def test_price_freshness_8_days_is_fail():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '16/07/2026', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result['status'] == 'fail'


def test_price_freshness_mixed_warn_and_fail_status_is_fail():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '17/07/2026', 'final_market_value': 100.0},  # 7 days -> warn
        {'asset_description': 'Fondo B', 'isin': 'LU0002',
         'last_price_update': '01/07/2026', 'final_market_value': 100.0},  # 23 days -> fail
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result['status'] == 'fail'
    assert len(result['detail']) == 2


def test_price_freshness_skips_blank_last_price_update():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '', 'final_market_value': 100.0},
    ])
    assert _check_price_freshness(calcs, date(2026, 7, 24)) is None


def test_price_freshness_future_price_date_clamped_to_ok():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '30/07/2026', 'final_market_value': 100.0},
    ])
    assert _check_price_freshness(calcs, date(2026, 7, 24)) is None


def test_price_freshness_check_shape():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '01/07/2026', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result['odt'] == 'CSV'
    assert result['group'] == 'CSV — Calidad datos'
    assert result['widget'] == 'Antigüedad de precios de activos'
    assert result['csv'] == '0 activos'
    assert result['json'] == '1 activo(s)'


def _minimal_jx(report_date_str):
    return {
        'pages': [
            {'widgets': [{'content': [{'data': {'value': 100, 'count': 1,
                                                 'date': report_date_str}}]}]},
        ],
        'W': {},
        'by_page': lambda pi, wid: None,
        'entities': [],
        'PI': {k: -1 for k in ['dist', 'dist_ent', 'kpi_boxes', 'familia', 'rf1', 'rf2', 'rv']},
    }


def _minimal_calcs(rows):
    df = pd.DataFrame(rows)
    empty = df.iloc[0:0]
    return {
        'total': 0.0, 'by_cust': {}, 'kpi_boxes': {}, 'lt_alloc': {}, 'lt_currency': {},
        'rf_total': 0.0, 'rv_total': 0.0,
        'unclassified': empty, 'missing_ac': empty, 'missing_sac': empty,
        'active': df,
    }


def test_run_checks_includes_price_freshness_failure():
    calcs = _minimal_calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '01/07/2026', 'final_market_value': 100.0},
    ])
    jx = _minimal_jx('24/07/2026')
    checks = run_checks(calcs, jx)
    freshness = [c for c in checks if c['widget'] == 'Antigüedad de precios de activos']
    assert len(freshness) == 1
    assert freshness[0]['status'] == 'fail'


def test_run_checks_skips_price_freshness_when_no_report_date():
    calcs = _minimal_calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '01/07/2026', 'final_market_value': 100.0},
    ])
    jx = _minimal_jx('')
    jx['pages'] = [{'widgets': []}]
    checks = run_checks(calcs, jx)
    freshness = [c for c in checks if c['widget'] == 'Antigüedad de precios de activos']
    assert freshness == []


def test_parse_date_iso_date():
    assert _parse_date('2026-07-22') == date(2026, 7, 22)


def test_parse_date_iso_datetime_with_microseconds():
    assert _parse_date('2026-07-24T06:00:25.364000') == date(2026, 7, 24)


def test_price_freshness_iso_format_last_price_update():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '2026-07-01', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result is not None
    assert result['status'] == 'fail'


def test_price_freshness_iso_datetime_last_price_update():
    calcs = _calcs([
        {'asset_description': 'Fondo A', 'isin': 'LU0001',
         'last_price_update': '2026-07-22T06:00:25.364000', 'final_market_value': 100.0},
    ])
    result = _check_price_freshness(calcs, date(2026, 7, 24))
    assert result is None  # 2 days old, well within the OK range
