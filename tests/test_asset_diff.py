import pytest
from src.diff import extract_assets, run_asset_diff
from src.diff import run_diff

_KPI_PAGE_A = {'layout': {'title': 'Pg'}, 'widgets': [{'name': 'kpi_box', 'title': 'X', 'content': [{'data': 100.0}]}]}
_KPI_PAGE_B = {'layout': {'title': 'Pg'}, 'widgets': [{'name': 'kpi_box', 'title': 'X', 'content': [{'data': 150.0}]}]}


def test_run_diff_period_labels_default_to_spanish():
    diffs = run_diff({'pages': [_KPI_PAGE_A]}, {'pages': [_KPI_PAGE_B]})
    assert len(diffs) == 1
    assert diffs[0]['date_a'] == 'Periodo A'
    assert diffs[0]['date_b'] == 'Periodo B'


def test_run_diff_period_labels_translate_to_english():
    diffs = run_diff({'pages': [_KPI_PAGE_A]}, {'pages': [_KPI_PAGE_B]}, lang='en')
    assert len(diffs) == 1
    assert diffs[0]['date_a'] == 'Period A'
    assert diffs[0]['date_b'] == 'Period B'


def _row(name, isin, mv):
    return {
        'type': 'row',
        'cells': [
            {'item': {'value': name, 'subvalue': isin}},
            {'item': {'value': '22/05/2026'}},
            {'item': {'value': 'eur'}},
            {'item': {'value': mv}},
            {'item': {'value': 100.0}},
            {'item': {'value': 0.1}},
        ],
    }


def _json(rows):
    return {
        'pages': [
            {
                'layout': {'title': 'Detalle'},
                'widgets': [
                    {
                        'name': 'table_full',
                        'id': 'table_full',
                        'content': [{'data': rows}],
                    }
                ],
            }
        ]
    }


def test_extract_assets_basic():
    data = _json([_row('Fondo A', 'LU0001', 100000.0)])
    result = extract_assets(data)
    assert result == {'LU0001': {'name': 'Fondo A', 'value': 100000.0}}


def test_extract_assets_skips_rows_without_isin():
    no_isin_row = {
        'type': 'row',
        'cells': [
            {'item': {'value': 'Total', 'subvalue': None}},
            {'item': {'value': '22/05/2026'}},
            {'item': {'value': 'eur'}},
            {'item': {'value': 500000.0}},
        ],
    }
    data = _json([_row('Fondo A', 'LU0001', 100000.0), no_isin_row])
    result = extract_assets(data)
    assert list(result.keys()) == ['LU0001']


def test_extract_assets_skips_non_table_full():
    data = {
        'pages': [{
            'layout': {'title': 'P'},
            'widgets': [{
                'name': 'table',
                'id': 'table_1',
                'content': [{'data': [_row('Fondo A', 'LU0001', 100000.0)]}],
            }],
        }]
    }
    result = extract_assets(data)
    assert result == {}


def test_run_asset_diff_changed():
    a = _json([_row('Fondo A', 'LU0001', 100000.0)])
    b = _json([_row('Fondo A', 'LU0001', 130000.0)])
    diffs = run_asset_diff(a, b)
    assert len(diffs) == 1
    d = diffs[0]
    assert d['isin'] == 'LU0001'
    assert d['status'] == 'changed'
    assert d['val_a'] == 100000.0
    assert d['val_b'] == 130000.0
    assert abs(d['pct_diff'] - 30.0) < 0.01
    assert d['sev'] == 'big'


def test_run_asset_diff_new():
    a = _json([])
    b = _json([_row('Fondo B', 'LU0002', 50000.0)])
    diffs = run_asset_diff(a, b)
    assert len(diffs) == 1
    assert diffs[0]['status'] == 'new'
    assert diffs[0]['val_a'] == 0
    assert diffs[0]['sev'] == 'big'


def test_run_asset_diff_removed():
    a = _json([_row('Fondo A', 'LU0001', 100000.0)])
    b = _json([])
    diffs = run_asset_diff(a, b)
    assert len(diffs) == 1
    assert diffs[0]['status'] == 'removed'
    assert diffs[0]['val_b'] == 0
    assert diffs[0]['pct_diff'] == -100.0
    assert diffs[0]['sev'] == 'big'


def test_run_asset_diff_severity():
    a = _json([
        _row('Big', 'LU0001', 100000.0),
        _row('Med', 'LU0002', 100000.0),
        _row('Sml', 'LU0003', 100000.0),
    ])
    b = _json([
        _row('Big', 'LU0001', 130000.0),   # +30% → big
        _row('Med', 'LU0002', 110000.0),   # +10% → medium
        _row('Sml', 'LU0003', 102000.0),   # +2%  → small
    ])
    diffs = run_asset_diff(a, b)
    by_isin = {d['isin']: d for d in diffs}
    assert by_isin['LU0001']['sev'] == 'big'
    assert by_isin['LU0002']['sev'] == 'medium'
    assert by_isin['LU0003']['sev'] == 'small'


def test_run_asset_diff_sorted_big_first():
    a = _json([_row('A', 'LU0001', 100000.0), _row('B', 'LU0002', 100000.0)])
    b = _json([_row('A', 'LU0001', 102000.0), _row('B', 'LU0002', 130000.0)])
    diffs = run_asset_diff(a, b)
    assert diffs[0]['isin'] == 'LU0002'  # big change first


def test_run_asset_diff_removed_abs_diff_positive():
    a = _json([_row('Fondo A', 'LU0001', -50000.0)])
    b = _json([])
    diffs = run_asset_diff(a, b)
    assert diffs[0]['abs_diff'] == 50000.0


def test_run_asset_diff_changed_from_zero_is_big():
    a = _json([_row('Fondo A', 'LU0001', 0.0)])
    b = _json([_row('Fondo A', 'LU0001', 50000.0)])
    diffs = run_asset_diff(a, b)
    assert diffs[0]['sev'] == 'big'
