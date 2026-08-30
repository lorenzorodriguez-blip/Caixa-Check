import pandas as pd

from src.market_data import build_market_data_sheets


def _row(**overrides):
    base = {
        'final_market_value': 100000.0, 'quantity': 1000.0, 'isin': 'LU0001',
        'asset_description': 'Test Fund', 'currency': 'eur', 'custodian': 'Test Bank',
        'asset_class_group': 'fund', 'sub_asset_class': 'mutual-fund',
        'investor_account': 'ACC1', 'date': '2026-08-30',
        'datapoints': "{'allocation_equity': 0.4, 'allocation_fixed-income': 0.6, "
                      "'currency_eur': 0.7, 'currency_usd': 0.3}",
        'exposures': '{}', 'pivolt_fields': '{}', 'portfolio_data': '{}',
    }
    base.update(overrides)
    return base


def test_fondos_record_converts_allocation_to_market_value():
    df = pd.DataFrame([_row()])
    _, fondos_records = build_market_data_sheets(df)

    assert len(fondos_records) == 1
    rec = fondos_records[0]
    # 0.4 -> 40% (via _r()) -> 100000 * 40 / 100 = 40000.0
    assert rec['Allocation_Equity'] == 40000.0
    assert rec['Allocation_Fixed Income'] == 60000.0
    assert rec['Currency_EUR'] == 70000.0
    assert rec['Currency_USD'] == 30000.0


def test_fondos_record_preserves_none_for_missing_allocation():
    df = pd.DataFrame([_row(datapoints="{'allocation_equity': 0.4}")])
    _, fondos_records = build_market_data_sheets(df)

    rec = fondos_records[0]
    assert rec['Allocation_Equity'] == 40000.0
    assert rec['Currency_EUR'] is None  # no currency datapoint supplied at all


def test_fondos_record_keeps_identity_fields_unchanged():
    df = pd.DataFrame([_row()])
    all_records, fondos_records = build_market_data_sheets(df)

    all_rec, fondos_rec = all_records[0], fondos_records[0]
    for identity_col in ('symbol', 'market_value', 'currency', 'custodian', 'asset_description'):
        assert fondos_rec[identity_col] == all_rec[identity_col]


def test_fondos_record_drops_ratio_columns():
    df = pd.DataFrame([_row(datapoints="{'alpha': 0.05, 'beta': 1.1, 'ter': 0.012}")])
    _, fondos_records = build_market_data_sheets(df)

    rec = fondos_records[0]
    for dropped_col in ('Alpha', 'Alpha_1', 'Beta', 'Beta_1', 'TER', 'TER_1'):
        assert dropped_col not in rec


def test_lookthrough_sheet_still_uses_full_md_columns_and_percentages():
    df = pd.DataFrame([_row()])
    all_records, _ = build_market_data_sheets(df)

    rec = all_records[0]
    assert rec['Allocation_Equity'] == 40.0  # still a percentage, unaffected
    assert 'Alpha' in rec  # ratio columns still present on look-through


def test_fondos_record_zero_market_value_gives_zero_not_error():
    df = pd.DataFrame([_row(final_market_value=0.0)])
    _, fondos_records = build_market_data_sheets(df)

    rec = fondos_records[0]
    assert rec['Allocation_Equity'] == 0.0
    assert rec['Currency_EUR'] == 0.0
