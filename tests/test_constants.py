# tests/test_constants.py
from src.constants import FONDOS_ALLOCATION_COLUMNS, FONDOS_MD_COLUMNS, MD_COLUMNS


def test_fondos_md_columns_drops_ratio_metrics_only():
    dropped = set(MD_COLUMNS) - set(FONDOS_MD_COLUMNS)
    assert dropped == {
        'Alpha', 'Alpha_1', 'Beta', 'Beta_1', 'TER', 'TER_1', 'TIR', 'TIR_1',
        'Volatility', 'Volatility_1', 'Duration', 'Duration_1', 'Cupon', 'Cupon_1',
        'Dividend', 'Dividend_1', 'PER', 'PER_1',
    }


def test_fondos_md_columns_keeps_order_and_no_duplicates():
    # Every kept column appears in FONDOS_MD_COLUMNS in the same relative order
    # as MD_COLUMNS, and nothing is duplicated or invented.
    filtered = [c for c in MD_COLUMNS if c in set(FONDOS_MD_COLUMNS)]
    assert filtered == FONDOS_MD_COLUMNS
    assert len(FONDOS_MD_COLUMNS) == len(set(FONDOS_MD_COLUMNS))


def test_fondos_allocation_columns_is_124_entries():
    assert len(FONDOS_ALLOCATION_COLUMNS) == 124


def test_fondos_allocation_columns_includes_expected_groups():
    for expected in ('Allocation_Equity', 'Currency_EUR', 'Rating Grade_AAA', 'Rating_AAA',
                      'Sector_FI_Government', 'Sector_EQ_Technology', 'Sector_Technology',
                      'Style_Large Growth', 'Maturity_1-3y', 'Region_EQ_UK', 'Region_FI_UK',
                      'Revenue VI_Eurozone'):
        assert expected in FONDOS_ALLOCATION_COLUMNS


def test_fondos_allocation_columns_excludes_identity_and_ratio_fields():
    for excluded in ('symbol', 'currency', 'sector', 'market_value', 'final_market_value',
                      'Rating', 'Maturity', 'Region', 'Alpha', 'Beta', 'TER', 'Duration', 'PER'):
        assert excluded not in FONDOS_ALLOCATION_COLUMNS


def test_fondos_allocation_columns_is_subset_of_fondos_md_columns():
    assert set(FONDOS_ALLOCATION_COLUMNS) <= set(FONDOS_MD_COLUMNS)
