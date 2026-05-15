import re

import pandas as pd

from .constants import KPI_SUBS
from .parser import safe_parse


def build_calcs(df: pd.DataFrame) -> dict:
    df = df.copy()
    df['_mv'] = pd.to_numeric(df.get('final_market_value', 0), errors='coerce').fillna(0)
    active = df[df['_mv'].abs() > 0.01].copy()

    total = float(active['_mv'].sum())

    by_cust = active.groupby('custodian')['_mv'].sum().to_dict() if 'custodian' in active.columns else {}

    kpi_boxes = {}
    for name, subs in KPI_SUBS.items():
        mask = active.get('sub_asset_class', pd.Series(dtype=str)).isin(subs)
        kpi_boxes[name] = float(active.loc[mask, '_mv'].sum())

    lt_alloc: dict = {}
    lt_currency: dict = {}

    for _, row in active.iterrows():
        val = float(row['_mv'])
        acg = str(row.get('asset_class_group', '') or '')
        currency = (str(row.get('currency', '') or '') or 'eur').lower()

        if acg == 'fund':
            exp = safe_parse(row.get('exposures', ''))
            if exp.get('allocation'):
                for k, v in exp['allocation'].items():
                    lt_alloc[k] = lt_alloc.get(k, 0.0) + float(v)
            else:
                lt_alloc[acg] = lt_alloc.get(acg, 0.0) + val
            if exp.get('currency'):
                for k, v in exp['currency'].items():
                    lt_currency[k] = lt_currency.get(k, 0.0) + float(v)
            else:
                lt_currency[currency] = lt_currency.get(currency, 0.0) + val
        else:
            key = acg if acg else 'other'
            lt_alloc[key] = lt_alloc.get(key, 0.0) + val
            lt_currency[currency] = lt_currency.get(currency, 0.0) + val

    def _empty_mask(col):
        return active.get(col, pd.Series(dtype=str)).fillna('').str.strip() == ''

    unclassified = active[_empty_mask('asset_class_group') & _empty_mask('sub_asset_class')]
    missing_ac   = active[_empty_mask('asset_class_group') & ~_empty_mask('sub_asset_class')]
    missing_sac  = active[~_empty_mask('asset_class_group') & _empty_mask('sub_asset_class')]

    return {
        'total':       total,
        'by_cust':     by_cust,
        'kpi_boxes':   kpi_boxes,
        'lt_alloc':    lt_alloc,
        'lt_currency': lt_currency,
        'rf_total':    lt_alloc.get('fixed-income', 0.0),
        'rv_total':    lt_alloc.get('equity', 0.0),
        'unclassified': unclassified,
        'missing_ac':   missing_ac,
        'missing_sac':  missing_sac,
        'active':       active,
    }


def extract_json(data: dict) -> dict:
    pages = data.get('pages', [])
    W: dict = {}

    for i, page in enumerate(pages):
        pt = (page.get('layout') or {}).get('title', '')
        for w in page.get('widgets', []):
            content = w.get('content') or []
            if not content:
                continue
            c = content[0]
            wid = w.get('id') or w.get('name')
            W[f'{i}_{wid}'] = {
                'page': i,
                'page_title': pt,
                'widget': wid,
                'name': w.get('name', ''),
                'wtitle': w.get('title', ''),
                'content': c,
            }

    def by_page(pi, wid):
        return W.get(f'{pi}_{wid}')

    entities = []
    for i, page in enumerate(pages):
        t = (page.get('layout') or {}).get('title', '')
        m = re.match(r'^(.+) - Distribución$', t)
        if m and 'por entidad' not in t:
            en = m.group(1).strip()
            rf_i = next(
                (j for j, p in enumerate(pages)
                 if en in ((p.get('layout') or {}).get('title', ''))
                 and 'renta fija' in ((p.get('layout') or {}).get('title', '')).lower()),
                -1,
            )
            rv_i = next(
                (j for j, p in enumerate(pages)
                 if en in ((p.get('layout') or {}).get('title', ''))
                 and 'renta variable' in ((p.get('layout') or {}).get('title', '')).lower()),
                -1,
            )
            entities.append({'name': en, 'dist_idx': i, 'rf_idx': rf_i, 'rv_idx': rv_i})

    def find_page(title_contains=None, name_exact=None, has_widget=None, nth=0):
        matches = []
        for i, p in enumerate(pages):
            t = ((p.get('layout') or {}).get('title', '') or '').lower()
            n = (p.get('layout') or {}).get('name', '')
            wids = [w.get('id') or w.get('name') or '' for w in p.get('widgets', [])]
            ok = True
            if title_contains and title_contains.lower() not in t:
                ok = False
            if name_exact and n != name_exact:
                ok = False
            if has_widget and has_widget not in wids:
                ok = False
            if ok:
                matches.append(i)
        return matches[nth] if len(matches) > nth else -1

    PI = {
        'dist':      find_page(name_exact='GridPage', title_contains='Distribución', has_widget='chart_1'),
        'dist_ent':  find_page(title_contains='Distribución de activos por entidad', has_widget='table_1'),
        'kpi_boxes': find_page(name_exact='FlexGridPage'),
        'familia':   find_page(title_contains='familia de producto'),
        'rf1':       find_page(title_contains='Exposición a renta fija', has_widget='table_1', nth=0),
        'rf2':       find_page(title_contains='Exposición a renta fija', has_widget='table_1', nth=1),
        'rv':        find_page(title_contains='Exposición a renta variable'),
    }

    return {'pages': pages, 'W': W, 'by_page': by_page, 'entities': entities, 'PI': PI}
