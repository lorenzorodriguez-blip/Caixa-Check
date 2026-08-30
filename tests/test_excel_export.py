from src.excel_export import build_excel


def test_build_excel_accepts_lang_kwarg():
    import pandas as pd
    df = pd.DataFrame([{'final_market_value': 100, 'custodian': 'Test', 'asset_class_group': 'cash',
                         'sub_asset_class': 'cash', 'isin': 'X', 'asset_description': 'Test asset',
                         'currency': 'eur'}])
    json_data = {'pages': []}
    # Should not raise, in either language.
    build_excel(df, json_data, lang='es')
    build_excel(df, json_data, lang='en')
