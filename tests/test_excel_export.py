import io

import openpyxl
import pandas as pd

from src.excel_export import build_excel
from src.i18n import t


def _make_inputs():
    df = pd.DataFrame([{'final_market_value': 100, 'custodian': 'Test', 'asset_class_group': 'cash',
                         'sub_asset_class': 'cash', 'isin': 'X', 'asset_description': 'Test asset',
                         'currency': 'eur'}])
    json_data = {'pages': []}
    return df, json_data


def _expected_headers(lang):
    return ['ODT', t('excel.col_group', lang), 'Widget / Check', t('excel.col_rule', lang),
            t('excel.col_expected_csv', lang), t('excel.col_actual_json', lang),
            t('excel.col_status', lang), 'Δ', t('excel.col_page', lang), 'Widget ID']


def test_build_excel_spanish_headers():
    df, json_data = _make_inputs()
    result = build_excel(df, json_data, lang='es')

    wb = openpyxl.load_workbook(io.BytesIO(result))

    assert wb.sheetnames[0] == t('excel.sheet_review', 'es')
    ws1 = wb[t('excel.sheet_review', 'es')]
    header_row = [cell.value for cell in ws1[1]]
    assert header_row == _expected_headers('es')

    assert t('excel.sheet_csv_data', 'es') in wb.sheetnames
    assert t('excel.sheet_funds', 'es') in wb.sheetnames


def test_build_excel_english_headers():
    df, json_data = _make_inputs()
    result = build_excel(df, json_data, lang='en')

    wb = openpyxl.load_workbook(io.BytesIO(result))

    assert wb.sheetnames[0] == t('excel.sheet_review', 'en')
    ws1 = wb[t('excel.sheet_review', 'en')]
    header_row = [cell.value for cell in ws1[1]]
    assert header_row == _expected_headers('en')

    assert t('excel.sheet_csv_data', 'en') in wb.sheetnames
    assert t('excel.sheet_funds', 'en') in wb.sheetnames
