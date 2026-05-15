import pandas as pd

from .constants import ASSET_CLASS_MAP_MD, FONDOS_GROUPS_MD, MD_COLUMNS
from .parser import safe_parse


def _dp_pct(dp: dict, key: str):
    v = dp.get(key)
    return round(v * 100 * 1e6) / 1e6 if v is not None else None


def _get_highest_rating(dp: dict) -> str:
    best_key, best_val = None, -1.0
    for k, v in dp.items():
        if k.startswith('credit_rating_') and isinstance(v, (int, float)) and v > best_val:
            best_val, best_key = v, k
    if not best_key or best_val <= 0:
        return 'No data'
    n = best_key.replace('credit_rating_', '')
    mapping = {'a': 'A', 'aa': 'AA', 'aaa': 'AAA', 'b': 'B', 'bb': 'BB',
               'bbb': 'BBB', 'nr': 'NR', 'other': 'Others', 'below_b': 'Below B'}
    return 'Rating_' + mapping.get(n, n.upper())


def transform_row(row: dict) -> dict:
    acg = (row.get('asset_class_group') or '').lower()
    dp  = safe_parse(row.get('datapoints', ''))
    exp = safe_parse(row.get('exposures', ''))
    pf  = safe_parse(row.get('pivolt_fields', ''))
    pd_ = safe_parse(row.get('portfolio_data', ''))

    asset_type, asset_class = ASSET_CLASS_MAP_MD.get(acg, ['Funds', acg])
    symbol = row.get('investor_account') if acg in ('cash', 'cash_equivalents') else row.get('isin')
    fmv    = float(row.get('final_market_value', 0) or 0)
    qty    = float(row.get('quantity', 0) or 0)
    mkt_price = fmv / qty if qty != 0 else fmv
    init_fx    = float(dp.get('initial_fx_rate', 1) or 1)
    current_fx = float(dp.get('current_fx_rate', 1) or 1)

    alloc_eq  = dp.get('allocation_equity', 0) or 0
    alloc_fi  = dp.get('allocation_fixed-income') or dp.get('allocation_fixed_income', 0) or 0
    alloc_mm  = dp.get('allocation_money_market', 0) or 0
    alloc_oth = dp.get('allocation_other') or dp.get('allocation_other_financials', 0) or 0
    alloc_csh = dp.get('allocation_cash') or dp.get('allocation_cash_equivalents', 0) or 0

    exp_cr = (exp or {}).get('credit_rating', {}) or {}

    def cr_pct(k):
        v = exp_cr.get(k)
        return round(v * 100 * 1e6) / 1e6 if v is not None else None

    def dp_pct(k):       return _dp_pct(dp, k)
    def reg_eq(k):       return dp_pct(f'region_equity_{k}')
    def reg_fi(k):       return dp_pct(f'region_fixedincome_{k}')
    def sec_eq(k):       return dp_pct(f'sector_equity_{k}')
    def sec_fi(k):       return dp_pct(f'sector_fixedincome_{k}')
    def rv_pct(k):       return dp_pct(f'revenue_vi_{k}')
    def sty_pct(k):      return dp_pct(f'style_{k}')
    def mat_pct(k):      return dp_pct(f'maturity_mat_{k}')
    def rg_pct(k):       return dp_pct(f'credit_rating_{k}')

    def _r(v):
        return round(v * 100 * 1e6) / 1e6 if v is not None else None

    investor_name = pf.get('investor_name') or pf.get('investor') or row.get('manager') or ''
    contact_name  = pd_.get('contact_long_name') or pd_.get('contact') or ''

    return {
        'symbol': symbol, 'date': row.get('date'),
        'investor_account': row.get('investor_account'),
        'quantity': qty or None, 'cost_basis': None,
        'market_value': fmv, 'local_market_value': float(row.get('local_market_value', 0) or 0),
        'position_gl': None, 'asset_description': row.get('asset_description'),
        'investor_id': row.get('portfolio_id'),
        'currency': (row.get('currency') or '').upper(),
        'custodian': row.get('custodian'), 'asset_type': asset_type, 'asset_class': asset_class,
        'sub_asset_class': row.get('sub_asset_class'), 'sector': row.get('sector'),
        'maturity_date': row.get('maturity'),
        'initial_fx_rate': init_fx, 'current_fx_rate': current_fx,
        'market_price': mkt_price, 'valuation_date': row.get('date'),
        'Allocation_Equity':            _r(alloc_eq)  if alloc_eq  else None,
        'Allocation_Fixed Income':      _r(alloc_fi)  if alloc_fi  else None,
        'Allocation_Money Market':      _r(alloc_mm)  if alloc_mm  else None,
        'Allocation_Other financials':  _r(alloc_oth) if alloc_oth else None,
        'Allocation_Cash & Equivalents':_r(alloc_csh) if alloc_csh else None,
        'Alpha_1':     _r(dp.get('alpha')),
        'Beta_1':      dp.get('beta'),
        'TER_1':       _r(dp.get('ter')),
        'TIR_1':       _r(dp.get('tir')),
        'Volatility_1':_r(dp.get('volatility')),
        'Duration_1':  dp.get('duration'),
        'Cupon_1':     _r(dp.get('cupon')),
        'Dividend_1':  _r(dp.get('dividend')),
        'PER_1':       dp.get('per'),
        'Currency_AUD': dp_pct('currency_aud'), 'Currency_BRL': dp_pct('currency_brl'),
        'Currency_CAD': dp_pct('currency_cad'), 'Currency_CHF': dp_pct('currency_chf'),
        'Currency_CNY': dp_pct('currency_cny'), 'Currency_DKK': dp_pct('currency_dkk'),
        'Currency_EUR': dp_pct('currency_eur'), 'Currency_GBP': dp_pct('currency_gbp'),
        'Currency_HKD': dp_pct('currency_hkd'), 'Currency_INR': dp_pct('currency_inr'),
        'Currency_JPY': dp_pct('currency_jpy'), 'Currency_KRW': dp_pct('currency_krw'),
        'Currency_MXN': dp_pct('currency_mxn'), 'Currency_NOK': dp_pct('currency_nok'),
        'Currency_SEK': dp_pct('currency_sek'), 'Currency_SGD': dp_pct('currency_sgd'),
        'Currency_TWD': dp_pct('currency_twd'), 'Currency_USD': dp_pct('currency_usd'),
        'Currency_Others': dp_pct('currency_other') or dp_pct('currency_others'),
        'Rating Grade_AAA': rg_pct('aaa'), 'Rating Grade_AA': rg_pct('aa'),
        'Rating Grade_A': rg_pct('a'), 'Rating Grade_BBB': rg_pct('bbb'),
        'Rating Grade_BB': rg_pct('bb'), 'Rating Grade_B': rg_pct('b'),
        'Rating Grade_Sin datos': rg_pct('nr') or rg_pct('no_data'),
        'Rating Grade_Others': rg_pct('other') or rg_pct('others'),
        'Rating_AAA': cr_pct('aaa'), 'Rating_AA': cr_pct('aa'), 'Rating_A': cr_pct('a'),
        'Rating_BBB': cr_pct('bbb'), 'Rating_BB': cr_pct('bb'), 'Rating_B': cr_pct('b'),
        'Rating_Below B': cr_pct('below_b'), 'Rating_NR': cr_pct('nr') or cr_pct('no_rating'),
        'Rating_Others': cr_pct('other') or cr_pct('others'),
        'Sector_FI_Corporate Bond': sec_fi('corporate_bond'),
        'Sector_FI_Government': sec_fi('government'),
        'Sector_FI_Gov. Related': sec_fi('government_related'),
        'Sector_FI_Asset Backed': sec_fi('asset_backed'),
        'Sector_FI_Covered Bond': sec_fi('covered_bond'),
        'Sector_FI_Cash & Equiv.': sec_fi('cash_&_equivalents'),
        'Sector_EQ_Technology': sec_eq('technology'),
        'Sector_EQ_Financial Services': sec_eq('financial_services'),
        'Sector_EQ_Healthcare': sec_eq('healthcare'),
        'Sector_EQ_Industrials': sec_eq('industrials'),
        'Sector_EQ_Consumer Cyclical': sec_eq('consumer_cyclical'),
        'Sector_EQ_Consumer Defensive': sec_eq('consumer_defensive'),
        'Sector_EQ_Communication Services': sec_eq('communication_services'),
        'Sector_EQ_Energy': sec_eq('energy'),
        'Sector_EQ_Basic Materials': sec_eq('basic_materials'),
        'Sector_EQ_Real Estate': sec_eq('real_estate'),
        'Sector_EQ_Utilities': sec_eq('utilities'),
        'Sector_EQ_Others': sec_eq('other') or sec_eq('others'),
        'Sector_Basic Materials': dp_pct('sector_basic_materials'),
        'Sector_Communication Services': dp_pct('sector_communication_services'),
        'Sector_Consumer Cyclical': dp_pct('sector_consumer_cyclical'),
        'Sector_Consumer Defensive': dp_pct('sector_consumer_defensive'),
        'Sector_Energy': dp_pct('sector_energy'),
        'Sector_Financial Services': dp_pct('sector_financial_services'),
        'Sector_Healthcare': dp_pct('sector_healthcare'),
        'Sector_Industrials': dp_pct('sector_industrials'),
        'Sector_Real Estate': dp_pct('sector_real_estate'),
        'Sector_Technology': dp_pct('sector_technology'),
        'Sector_Others': dp_pct('sector_other') or dp_pct('sector_others'),
        'Style_Large Growth': sty_pct('large_growth'), 'Style_Large Core': sty_pct('large_core'),
        'Style_Large Value': sty_pct('large_value'), 'Style_Mid Growth': sty_pct('mid_growth'),
        'Style_Mid Core': sty_pct('mid_core'), 'Style_Mid Value': sty_pct('mid_value'),
        'Style_Small Growth': sty_pct('small_growth'), 'Style_Small Core': sty_pct('small_core'),
        'Style_Small Value': sty_pct('small_value'),
        'Style_Others': sty_pct('other') or sty_pct('others'),
        'Maturity_<182d': mat_pct('91_182d') or mat_pct('1_7d'),
        'Maturity_182d-365d': mat_pct('183_364d'),
        'Maturity_1-3y': mat_pct('1_3y'), 'Maturity_3-5y': mat_pct('3_5y'),
        'Maturity_5-7y': mat_pct('5_7y'), 'Maturity_7-10y': mat_pct('7_10y'),
        'Maturity_10-15y': mat_pct('10_15y'), 'Maturity_15-20y': mat_pct('15_20y'),
        'Maturity_20-30y': mat_pct('20_30y'), 'Maturity_>30y': mat_pct('30y+'),
        'Region_EQ_North America': reg_eq('north_america'),
        'Region_EQ_Europe Dev': reg_eq('europe_dev'), 'Region_EQ_UK': reg_eq('united_kingdom'),
        'Region_EQ_Japan': reg_eq('japan'), 'Region_EQ_Asia Dev': reg_eq('asia_dev'),
        'Region_EQ_Asia Emrg': reg_eq('asia_emrg'), 'Region_EQ_Australasia': reg_eq('australasia'),
        'Region_EQ_LATAM': reg_eq('latin_america'), 'Region_EQ_Europe Emrg': reg_eq('europe_emrg'),
        'Region_EQ_Africa/ME': reg_eq('africa_middle_east'),
        'Region_FI_North America': reg_fi('north_america'),
        'Region_FI_Europe Dev': reg_fi('europe_dev'), 'Region_FI_UK': reg_fi('united_kingdom'),
        'Region_FI_Japan': reg_fi('japan'), 'Region_FI_Asia Dev': reg_fi('asia_dev'),
        'Region_FI_Asia Emrg': reg_fi('asia_emrg'), 'Region_FI_Australasia': reg_fi('australasia'),
        'Region_FI_LATAM': reg_fi('latin_america'), 'Region_FI_Europe Emrg': reg_fi('europe_emrg'),
        'Region_FI_Africa/ME': reg_fi('africa_middle_east'),
        'Revenue VI_Eurozone': rv_pct('eurozone'), 'Revenue VI_Europe Ex eur': rv_pct('europe_ex_eur'),
        'Revenue VI_USA': rv_pct('usa'), 'Revenue VI_Canada': rv_pct('canada'),
        'Revenue VI_Japan': rv_pct('japan'), 'Revenue VI_Developed Asia': rv_pct('developed_asia'),
        'Revenue VI_Australasia': rv_pct('australasia'), 'Revenue VI_Emerging Asia': rv_pct('emerging_asia'),
        'Revenue VI_Emerging Europe': rv_pct('emerging_europe'), 'Revenue VI_LATAM': rv_pct('latam'),
        'Revenue VI_Africa': rv_pct('africa'), 'Revenue VI_Middle East': rv_pct('middle_east'),
        'Revenue VI_UK': rv_pct('uk'), 'Revenue VI_Others': rv_pct('other') or rv_pct('others'),
        'Highest_Rating': _get_highest_rating(dp), 'final_market_value': fmv,
        'asset_class_group': asset_class,
        'TIR': _r(dp.get('tir')), 'Rating': _get_highest_rating(dp),
        'Duration': dp.get('duration'), 'Cupon': _r(dp.get('cupon')),
        'Maturity': row.get('maturity'), 'PER': dp.get('per'),
        'Dividend': _r(dp.get('dividend')), 'Volatility': _r(dp.get('volatility')),
        'TER': _r(dp.get('ter')), 'Alpha': _r(dp.get('alpha')), 'Beta': dp.get('beta'),
        'Region': row.get('region'), 'isin': row.get('isin'),
        'last_price_update': row.get('last_price_update'),
        'risk_type': row.get('risk_type'), 'service_type': row.get('service_type'),
        'investor': investor_name or None, 'contact': contact_name or None,
        'investor_name': investor_name or None,
    }


def build_market_data_sheets(df: pd.DataFrame) -> tuple[list, list]:
    all_records, fondos_records = [], []
    for row in df.to_dict('records'):
        acg = (row.get('asset_class_group') or '').lower()
        rec = transform_row(row)
        all_records.append(rec)
        if acg in FONDOS_GROUPS_MD:
            fondos_records.append(rec)
    return all_records, fondos_records
