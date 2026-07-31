from datetime import datetime

from .constants import TOL, PCT_TOL


def _parse_date(s):
    """Parse a date string in 'dd/mm/yyyy' or ISO 8601 (date or datetime) format."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    try:
        return datetime.strptime(s, '%d/%m/%Y').date()
    except ValueError:
        pass
    try:
        return datetime.strptime(s[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _report_date(jx):
    """Find the report's date by scanning all widgets for the first content.data.date field."""
    for page in jx.get('pages', []):
        for w in page.get('widgets', []):
            for c in (w.get('content') or []):
                d = c.get('data')
                if isinstance(d, dict) and d.get('date'):
                    parsed = _parse_date(d['date'])
                    if parsed:
                        return parsed
    return None


def fmt(v) -> str:
    if v is None:
        return '—'
    return f'{v:,.0f} €'.replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_p(v: float) -> str:
    return f'{v * 100:.2f}%'


def pct_sum(arr: list) -> float:
    return sum(r.get('percentage', 0) or 0 for r in (arr or []))


def val_sum(arr: list) -> float:
    return sum(r.get('value', 0) or 0 for r in (arr or []))


def chk(odt, group, widget, rule, csv_val, json_val, mode='abs', page_title='', widget_id='') -> dict:
    if mode == 'pct100':
        d = abs(json_val - 1)
        status = 'pass' if d < PCT_TOL else 'warn' if d < 0.02 else 'fail'
        csv_str, json_str = '100,00%', fmt_p(json_val)
        detail = [] if d < PCT_TOL else [f'Δ {d * 100:.2f}pp']

    elif mode == 'no_negative':
        status = 'pass' if json_val >= 0 else 'fail'
        csv_str, json_str = '≥ 0', fmt(json_val)
        detail = [f'Negativo: {fmt(json_val)}'] if json_val < 0 else []

    elif mode == 'match_pct':
        d = abs(csv_val - json_val)
        status = 'pass' if d < PCT_TOL else 'warn' if d < 0.02 else 'fail'
        csv_str, json_str = fmt_p(csv_val), fmt_p(json_val)
        detail = [] if d < 0.001 else [f'Δ {d * 100:.2f}pp']

    elif mode == 'match_value':
        d = abs(csv_val - json_val)
        tol = max(TOL, abs(csv_val) * 0.02)
        status = 'pass' if d <= tol else 'warn' if d <= abs(csv_val) * 0.05 else 'fail'
        csv_str, json_str = fmt(csv_val), fmt(json_val)
        detail = [] if d < 0.5 else [f'Δ {fmt(d)}']

    else:  # abs
        d = abs(csv_val - json_val)
        status = 'pass' if d <= TOL else 'warn' if d <= abs(csv_val or 1) * 0.02 else 'fail'
        csv_str, json_str = fmt(csv_val), fmt(json_val)
        detail = [] if d < 0.5 else [f'Δ {fmt(d)}']

    return {
        'odt': odt, 'group': group, 'widget': widget, 'rule': rule,
        'csv': csv_str, 'json': json_str, 'status': status, 'detail': detail,
        'page_title': page_title, 'widget_id': widget_id,
    }


def _collect_pct_items(obj):
    """Recursively collect every dict that contains a 'percentage' key."""
    found = []
    if isinstance(obj, list):
        for item in obj:
            found.extend(_collect_pct_items(item))
    elif isinstance(obj, dict):
        if 'percentage' in obj:
            found.append(obj)
        else:
            for v in obj.values():
                found.extend(_collect_pct_items(v))
    return found


def _check_dist_rows(items, odt, group, widget, page_title='', widget_id=''):
    """Check distribution items for negative (<-0.1%) or overlarge (>100%) percentages."""
    if not items:
        return None
    bad = []
    for r in items:
        pct = r.get('percentage') or 0
        val = r.get('value') or 0
        if pct < -0.001 or pct > 1.0:
            tag = ' [supera 100%]' if pct > 1.0 else ''
            severity = 'high' if abs(pct) > 0.05 or pct > 1.0 else 'low'
            bad.append((severity, f"{r.get('name', '?')}: {pct * 100:+.2f}%  ({fmt(val)}){tag}"))
    if not bad:
        return None
    return {
        'odt': odt, 'group': group, 'widget': widget,
        'rule': 'Sin porcentajes negativos ni > 100%',
        'csv': '0 anomalías', 'json': f'{len(bad)} fila(s)',
        'status': 'fail' if any(s == 'high' for s, _ in bad) else 'warn',
        'detail': [label for _, label in bad],
        'page_title': page_title, 'widget_id': widget_id,
    }


def _check_price_freshness(calcs, report_date):
    """Flag assets whose last_price_update is stale relative to the report date."""
    bad = []
    for r in calcs['active'].to_dict('records'):
        price_date = _parse_date(r.get('last_price_update'))
        if price_date is None:
            continue
        diff_days = max(0, (report_date - price_date).days)
        if diff_days <= 3:
            continue
        severity = 'warn' if diff_days <= 7 else 'fail'
        tag = 'ALERTA' if severity == 'warn' else 'ERROR'
        bad.append((severity,
                     f"{r.get('asset_description', '—')} | ISIN: {r.get('isin', '—')} | "
                     f"precio: {r.get('last_price_update')} | {diff_days} día(s) [{tag}]"))
    if not bad:
        return None
    return {
        'odt': 'CSV', 'group': 'CSV — Calidad datos',
        'widget': 'Antigüedad de precios de activos',
        'rule': 'last_price_update dentro de la semana del informe (≤3 días OK, 4-7 alerta, ≥8 error)',
        'csv': '0 activos', 'json': f'{len(bad)} activo(s)',
        'status': 'fail' if any(s == 'fail' for s, _ in bad) else 'warn',
        'detail': [msg for _, msg in bad],
        'page_title': '', 'widget_id': '',
    }


def _kpi_val(d):
    if d is None:
        return None
    return d.get('value', 0) if isinstance(d, dict) else d


def run_checks(calcs: dict, jx: dict) -> list:
    checks = []
    by_page = jx['by_page']
    entities = jx['entities']
    PI = jx['PI']

    def gd(pi, wid):
        w = by_page(pi, wid)
        return w['content'].get('data') if w else None

    def wp(pi, wid):
        w = by_page(pi, wid)
        return (w.get('page_title', '') if w else ''), (wid or '')

    def fmt_row(r):
        mv = float(r.get('final_market_value', 0) or 0)
        return (f"{r.get('asset_description', '—')} | ISIN: {r.get('isin', '—')} | "
                f"{r.get('custodian', '—')} | MV: {fmt(mv)} | "
                f"asset_class: \"{r.get('asset_class_group', '')}\" | "
                f"sub_asset: \"{r.get('sub_asset_class', '')}\"")

    # ── CSV quality checks ──────────────────────────────────────────────────
    if len(calcs['unclassified']) > 0:
        detail = [fmt_row(r) for r in calcs['unclassified'].to_dict('records')]
        checks.append({'odt': 'CSV', 'group': 'CSV — Calidad datos',
                        'widget': 'Activos sin asset_class ni sub_asset_class',
                        'rule': 'MV > 0 pero faltan ambas clasificaciones',
                        'csv': '0 activos', 'json': f"{len(calcs['unclassified'])} activo(s)",
                        'status': 'fail', 'detail': detail, 'page_title': '', 'widget_id': ''})
    else:
        checks.append({'odt': 'CSV', 'group': 'CSV — Calidad datos',
                        'widget': 'Activos sin asset_class ni sub_asset_class',
                        'rule': 'MV > 0 pero faltan ambas clasificaciones',
                        'csv': '0 activos', 'json': '0 activos',
                        'status': 'pass', 'detail': [], 'page_title': '', 'widget_id': ''})

    if len(calcs['missing_ac']) > 0:
        detail = [fmt_row(r) for r in calcs['missing_ac'].to_dict('records')]
        checks.append({'odt': 'CSV', 'group': 'CSV — Calidad datos',
                        'widget': 'Activos sin asset_class_group',
                        'rule': 'MV > 0, tiene sub_asset_class pero falta asset_class_group',
                        'csv': '0 activos', 'json': f"{len(calcs['missing_ac'])} activo(s)",
                        'status': 'warn', 'detail': detail, 'page_title': '', 'widget_id': ''})

    if len(calcs['missing_sac']) > 0:
        detail = [fmt_row(r) for r in calcs['missing_sac'].to_dict('records')]
        checks.append({'odt': 'CSV', 'group': 'CSV — Calidad datos',
                        'widget': 'Activos sin sub_asset_class',
                        'rule': 'MV > 0, tiene asset_class_group pero falta sub_asset_class',
                        'csv': '0 activos', 'json': f"{len(calcs['missing_sac'])} activo(s)",
                        'status': 'warn', 'detail': detail, 'page_title': '', 'widget_id': ''})

    report_date = _report_date(jx)
    if report_date:
        freshness_check = _check_price_freshness(calcs, report_date)
        if freshness_check:
            checks.append(freshness_check)

    # ── Global KPI ──────────────────────────────────────────────────────────
    global_kpi = _kpi_val(gd(PI['dist'], 'kpi_list_1'))
    if global_kpi is not None:
        checks.append(chk('—', 'Global', 'Valoración actual total',
                           'CSV sum(final_market_value) = JSON KPI total',
                           calcs['total'], global_kpi, 'abs', *wp(PI['dist'], 'kpi_list_1')))

    # ── Widget 1: Distribución por entidad ──────────────────────────────────
    ent_t = gd(PI['dist'], 'table_1')
    if ent_t:
        checks.append(chk('1', '1) Dist. entidad financiera', '% suma = 100%',
                           'Suma porcentajes entidades = 100%',
                           None, pct_sum(ent_t), 'pct100', *wp(PI['dist'], 'table_1')))
        checks.append(chk('1', '1) Dist. entidad financiera', 'Σ importes = Valoración actual',
                           'Total entidades = total patrimonio',
                           calcs['total'], val_sum(ent_t), 'abs', *wp(PI['dist'], 'table_1')))
        for r in ent_t:
            checks.append(chk('1', f"1) {r['name']}", 'Importe = CSV por custodian',
                               f"{r['name']}: CSV vs JSON",
                               calcs['by_cust'].get(r['name'], 0), r.get('value', 0)))

    # ── Widget 2: Distribución activos LT ───────────────────────────────────
    asset_c = gd(PI['dist'], 'chart_1')
    if asset_c:
        checks.append(chk('2', '2) Dist. activos LT', '% suma = 100%',
                           'Suma % clases de activo = 100%',
                           None, pct_sum(asset_c), 'pct100', *wp(PI['dist'], 'chart_1')))
        AL = {'fixed-income': 'RF', 'equity': 'RV', 'cash': 'Liquidez', 'alternative': 'Alt.', 'other': 'Otros'}
        for r in asset_c:
            checks.append(chk('2', f"2) {AL.get(r['name'], r['name'])}", 'LT CSV = JSON chart',
                               'exposures.allocation + asset_class_group',
                               calcs['lt_alloc'].get(r['name'], 0), r.get('value', 0), 'match_value'))

    # ── Widget 3: Distribución divisa LT ────────────────────────────────────
    curr_c = gd(PI['dist'], 'chart_2')
    if curr_c:
        checks.append(chk('3', '3) Dist. divisa LT', '% suma ≈ 100%',
                           'Suma % divisas LT = 100%',
                           None, pct_sum(curr_c), 'pct100', *wp(PI['dist'], 'chart_2')))

    # ── Widget 4: Tabla activos x entidad ───────────────────────────────────
    dist_t = gd(PI['dist_ent'], 'table_1')
    if dist_t:
        dist_entities = [r for r in dist_t if r.get('name') != 'total']
        dist_total_row = next((r for r in dist_t if r.get('name') == 'total'), None)
        grand = 0.0
        if dist_total_row:
            tot = next((d for d in (dist_total_row.get('distribution') or []) if d.get('name') == 'total'), None)
            if tot:
                grand = tot.get('value', 0)
        else:
            for cr in dist_entities:
                tot = next((d for d in (cr.get('distribution') or []) if d.get('name') == 'total'), None)
                if tot:
                    grand += tot.get('value', 0)

        checks.append(chk('4', '4) Tabla activos x entidad', 'Total = Valoración actual (widget 1)',
                           'Grand total tabla = total patrimonio',
                           calcs['total'], grand, 'abs', *wp(PI['dist_ent'], 'table_1')))
        for cr in dist_entities:
            tot = next((d for d in (cr.get('distribution') or []) if d.get('name') == 'total'), None)
            if tot:
                checks.append(chk('4', f"4) {cr['name']} — total fila", 'Total fila = valoración entidad',
                                   f"Fila {cr['name']}",
                                   calcs['by_cust'].get(cr['name'], 0), tot.get('value', 0)))
        if asset_c:
            AL = {'fixed-income': 'RF', 'equity': 'RV', 'cash': 'Liquidez', 'alternative': 'Alt.', 'other': 'Otros'}
            for gi in asset_c:
                col_tot = 0.0
                if dist_total_row:
                    cell = next((d for d in (dist_total_row.get('distribution') or []) if d.get('name') == gi['name']), None)
                    if cell:
                        col_tot = cell.get('value', 0)
                else:
                    for cr in dist_entities:
                        cell = next((d for d in (cr.get('distribution') or []) if d.get('name') == gi['name']), None)
                        if cell:
                            col_tot += cell.get('value', 0)
                checks.append(chk('4', f"4) Columna {AL.get(gi['name'], gi['name'])} = widget 2",
                                   '% columna tabla = % dist. activos (widget 2)',
                                   'Porcentajes por tipo activo coinciden',
                                   gi.get('value', 0), col_tot, 'match_value'))

    # ── Widget 6: kpi_boxes tipo producto ───────────────────────────────────
    all_kpi = [w for w in jx['W'].values() if w.get('name') == 'kpi_box']
    if all_kpi:
        k_sum = sum(_kpi_val(w['content'].get('data')) or 0 for w in all_kpi)
        page_title = (jx['pages'][PI['dist']].get('layout') or {}).get('title', '') if PI['dist'] >= 0 else ''
        checks.append(chk('6', '6) kpi_boxes tipo producto', 'Σ = Valoración actual (widget 1)',
                           'Suma kpi_boxes = total patrimonio',
                           calcs['total'], k_sum, 'abs', page_title, 'kpi_box'))

    # ── Widget 7: Tabla familia producto ────────────────────────────────────
    fam_t = gd(PI['familia'], 'table_1')
    if fam_t:
        fam_entities = [r for r in fam_t if r.get('name') != 'total']
        fam_total_row = next((r for r in fam_t if r.get('name') == 'total'), None)
        fam_grand = 0.0
        if fam_total_row:
            tot = next((d for d in (fam_total_row.get('distribution') or []) if d.get('name') == 'total'), None)
            if tot:
                fam_grand = tot.get('value', 0)
        else:
            for cr in fam_entities:
                tot = next((d for d in (cr.get('distribution') or []) if d.get('name') == 'total'), None)
                if tot:
                    fam_grand += tot.get('value', 0)
        checks.append(chk('7', '7) Tabla familia producto', 'Total = Valoración actual (widgets 1 y 6)',
                           'Grand total tabla familia = total patrimonio',
                           calcs['total'], fam_grand, 'abs', *wp(PI['familia'], 'table_1')))
        for cr in fam_entities:
            tot = next((d for d in (cr.get('distribution') or []) if d.get('name') == 'total'), None)
            if tot:
                checks.append(chk('7', f"7) {cr['name']} — total fila", 'Total fila = valoración entidad',
                                   f"Familia total {cr['name']}",
                                   calcs['by_cust'].get(cr['name'], 0), tot.get('value', 0)))

    # ── Widgets 8-14: Renta Fija ─────────────────────────────────────────────
    rf_kpi_w = by_page(PI['rf1'], 'kpi_list') or by_page(PI['rf2'], 'kpi_list')
    rf_jv = None
    if rf_kpi_w:
        d = rf_kpi_w['content'].get('data')
        rf_jv = d.get('value', d) if isinstance(d, dict) else d
        checks.append(chk('10', '10) Inv. total RF', 'Valor = widget 4 total RF (LT)',
                           'Sum LT fixed-income CSV = KPI RF JSON',
                           calcs['rf_total'], rf_jv, 'match_value', *wp(PI['rf1'], 'kpi_list')))
        if asset_c:
            ri = next((r for r in asset_c if r.get('name') == 'fixed-income'), None)
            if ri:
                json_pct = rf_kpi_w['content'].get('data', {})
                json_pct = json_pct.get('percentage', 0) if isinstance(json_pct, dict) else 0
                checks.append(chk('10', '10) Inv. total RF', '% = % RF de widget 2',
                                   '% RF KPI = % RF en dist.activos LT',
                                   ri.get('percentage', 0), json_pct, 'match_pct'))

    rf_ent_t = gd(PI['rf1'], 'table_1')
    if rf_ent_t:
        checks.append(chk('8', '8) RF — dist. entidad', '% suma = 100%',
                           'Suma % entidades dentro RF = 100%',
                           None, pct_sum(rf_ent_t), 'pct100', *wp(PI['rf1'], 'table_1')))
        if rf_jv is not None:
            checks.append(chk('8', '8) RF — dist. entidad', 'Total = inv. total RF (widget 10)',
                               'Suma importes RF por entidad = KPI RF',
                               rf_jv, val_sum(rf_ent_t), 'match_value', *wp(PI['rf1'], 'table_1')))
        if dist_t:
            for r in rf_ent_t:
                cr = next((c for c in dist_t if c.get('name') == r.get('name')), None)
                if cr:
                    cell = next((d for d in (cr.get('distribution') or []) if d.get('name') == 'fixed-income'), None)
                    if cell:
                        checks.append(chk('8', f"8) RF — {r['name']}", 'RF entidad = widget 4 RF entidad',
                                           'Valor RF entidad vs tabla activos x entidad',
                                           cell.get('value', 0), r.get('value', 0), 'match_value'))

    rf_prod_t = gd(PI['rf1'], 'table_2')
    if rf_prod_t:
        checks.append(chk('9', '9) RF — tipo producto', '% suma = 100%',
                           'Suma % tipos producto RF = 100%',
                           None, pct_sum(rf_prod_t), 'pct100', *wp(PI['rf1'], 'table_2')))
        if rf_jv is not None:
            checks.append(chk('9', '9) RF — tipo producto', 'Total = inv. total RF',
                               'Suma tipos producto = KPI RF',
                               rf_jv, val_sum(rf_prod_t), 'match_value', *wp(PI['rf1'], 'table_2')))

    rf_em_c = gd(PI['rf2'], 'chart_1')
    if rf_em_c:
        checks.append(chk('11', '11) RF — emisor', '% suma = 100%',
                           'Suma % tipos emisor RF = 100%',
                           None, pct_sum(rf_em_c), 'pct100', *wp(PI['rf2'], 'chart_1')))
        for r in rf_em_c:
            checks.append(chk('11', f"11) RF — emisor {r['name']}", 'Sin valores negativos',
                               'Valores emisor RF ≥ 0', None, r.get('value', 0), 'no_negative'))

    rf_rat_t = gd(PI['rf2'], 'table_1')
    if rf_rat_t:
        checks.append(chk('12', '12) RF — calificación crediticia', '% suma = 100%',
                           'Suma % ratings RF = 100%',
                           None, pct_sum(rf_rat_t), 'pct100', *wp(PI['rf2'], 'table_1')))
        if rf_jv is not None:
            checks.append(chk('12', '12) RF — calificación crediticia', 'Σ importe = inv. total RF (widget 10)',
                               'Suma importes rating = KPI RF',
                               rf_jv, val_sum(rf_rat_t), 'match_value', *wp(PI['rf2'], 'table_1')))

    rf_geo_c = gd(PI['rf2'], 'chart_2')
    if rf_geo_c:
        checks.append(chk('13', '13) RF — geografía', '% suma = 100%',
                           'Suma % geografía RF = 100%',
                           None, pct_sum(rf_geo_c), 'pct100', *wp(PI['rf2'], 'chart_2')))

    rf_venc_t = gd(PI['rf2'], 'table_2')
    if rf_venc_t and val_sum(rf_venc_t) > 0:
        checks.append(chk('14', '14) RF — vencimientos', '% suma = 100%',
                           'Suma % vencimientos RF = 100%',
                           None, pct_sum(rf_venc_t), 'pct100', *wp(PI['rf2'], 'table_2')))

    # ── Widgets 15-18: Renta Variable ───────────────────────────────────────
    rv_kpi_w = by_page(PI['rv'], 'kpi_list')
    rv_jv = None
    if rv_kpi_w:
        d = rv_kpi_w['content'].get('data')
        rv_jv = d.get('value', d) if isinstance(d, dict) else d
        checks.append(chk('15', '15) Inv. total RV', 'Valor = widget 4 total RV (LT)',
                           'Sum LT equity CSV = KPI RV JSON',
                           calcs['rv_total'], rv_jv, 'match_value', *wp(PI['rv'], 'kpi_list')))
        if asset_c:
            ri = next((r for r in asset_c if r.get('name') == 'equity'), None)
            if ri:
                json_pct = rv_kpi_w['content'].get('data', {})
                json_pct = json_pct.get('percentage', 0) if isinstance(json_pct, dict) else 0
                checks.append(chk('15', '15) Inv. total RV', '% = % RV de widget 2',
                                   '% RV KPI = % RV en dist.activos LT',
                                   ri.get('percentage', 0), json_pct, 'match_pct'))

    rv_ent_t = gd(PI['rv'], 'table_1')
    if rv_ent_t:
        checks.append(chk('16', '16) RV — dist. entidad', '% suma = 100%',
                           'Suma % entidades dentro RV = 100%',
                           None, pct_sum(rv_ent_t), 'pct100', *wp(PI['rv'], 'table_1')))
        if rv_jv is not None:
            checks.append(chk('16', '16) RV — dist. entidad', 'Total = inv. total RV (widget 15)',
                               'Suma RV por entidad = KPI RV',
                               rv_jv, val_sum(rv_ent_t), 'match_value', *wp(PI['rv'], 'table_1')))
        if dist_t:
            for r in rv_ent_t:
                cr = next((c for c in dist_t if c.get('name') == r.get('name')), None)
                if cr:
                    cell = next((d for d in (cr.get('distribution') or []) if d.get('name') == 'equity'), None)
                    if cell:
                        checks.append(chk('16', f"16) RV — {r['name']}", 'RV entidad = widget 4 RV entidad',
                                           'Valor RV entidad vs tabla activos x entidad',
                                           cell.get('value', 0), r.get('value', 0), 'match_value'))

    rv_geo_c = gd(PI['rv'], 'chart_bar_1')
    if rv_geo_c:
        checks.append(chk('17', '17) RV — geografía', '% suma = 100%',
                           'Suma % geografía RV = 100%',
                           None, pct_sum(rv_geo_c), 'pct100', *wp(PI['rv'], 'chart_bar_1')))

    rv_sec_t = gd(PI['rv'], 'table_2')
    if rv_sec_t:
        checks.append(chk('18', '18) RV — sector', '% suma = 100%',
                           'Suma % sectores RV = 100%',
                           None, pct_sum(rv_sec_t), 'pct100', *wp(PI['rv'], 'table_2')))
        if rv_jv is not None:
            checks.append(chk('18', '18) RV — sector', 'Σ importe = inv. total RV (widget 15)',
                               'Suma importes sectores = KPI RV',
                               rv_jv, val_sum(rv_sec_t), 'match_value', *wp(PI['rv'], 'table_2')))

    # ── Widgets 19a-31a: Por entidad ─────────────────────────────────────────
    for ent in entities:
        en, di = ent['name'], ent['dist_idx']
        csv_cust = calcs['by_cust'].get(en, 0)

        e_kpi = _kpi_val(gd(di, 'kpi_list_1'))
        if e_kpi is not None:
            checks.append(chk('19a', f'{en} — 19a) Valoración actual',
                               '= widget 4 total entidad', 'KPI entidad = valoración en tabla activos',
                               csv_cust, e_kpi))

        e_as_c = gd(di, 'chart_1')
        if e_as_c:
            checks.append(chk('20a', f'{en} — 20a) Dist. activos LT', '% suma = 100%',
                               'Suma % LT activos entidad = 100%', None, pct_sum(e_as_c), 'pct100'))
            if dist_t:
                cr4 = next((c for c in dist_t if c.get('name') != 'total' and c.get('name') == en), None)
                tot4 = next((d for d in (cr4.get('distribution') or []) if d.get('name') == 'total'), None) if cr4 else None
                if cr4 and tot4:
                    for item in e_as_c:
                        cell4 = next((d for d in (cr4.get('distribution') or []) if d.get('name') == item.get('name')), None)
                        if cell4 and tot4.get('value'):
                            pct4 = cell4.get('value', 0) / tot4['value']
                            checks.append(chk('20a', f"{en} — 20a) {item['name']} %",
                                               '% = widget 4 % por entidad',
                                               '% activo entidad coincide con tabla widget 4',
                                               pct4, item.get('percentage', 0), 'match_pct'))

        e_fam_t = gd(di, 'table_1')
        if e_fam_t:
            checks.append(chk('21a', f'{en} — 21a) Familia producto', '% suma = 100%',
                               'Suma % familia producto entidad = 100%', None, pct_sum(e_fam_t), 'pct100'))
            if e_kpi is not None:
                checks.append(chk('21a', f'{en} — 21a) Familia producto',
                                   'Σ valoración = 19a valoración actual', 'Suma familia = KPI entidad',
                                   e_kpi, val_sum(e_fam_t)))

        e_cur_c = gd(di, 'chart_2')
        if e_cur_c:
            checks.append(chk('22a', f'{en} — 22a) Divisa LT', '% suma ≈ 100%',
                               'Suma % divisas entidad = 100%', None, pct_sum(e_cur_c), 'pct100'))

        if ent['rf_idx'] >= 0:
            ri = ent['rf_idx']
            e_rf_kpi = by_page(ri, 'kpi_list')
            e_rf_d = e_rf_kpi['content'].get('data') if e_rf_kpi else None
            e_rf_v = e_rf_d.get('value', e_rf_d) if isinstance(e_rf_d, dict) else e_rf_d

            if e_rf_kpi and dist_t:
                cr4 = next((c for c in dist_t if c.get('name') != 'total' and c.get('name') == en), None)
                if cr4:
                    rf_cell = next((d for d in (cr4.get('distribution') or []) if d.get('name') == 'fixed-income'), None)
                    tot4 = next((d for d in (cr4.get('distribution') or []) if d.get('name') == 'total'), None)
                    if rf_cell:
                        checks.append(chk('23a', f'{en} — 23a) Inv. total RF',
                                           'Valor = widget 4 RF entidad',
                                           'KPI RF entidad = RF entidad en tabla global',
                                           rf_cell.get('value', 0), e_rf_v, 'match_value'))
                        if tot4 and tot4.get('value'):
                            pct_rf = rf_cell.get('value', 0) / tot4['value']
                            e_rf_pct = e_rf_d.get('percentage', 0) if isinstance(e_rf_d, dict) else 0
                            checks.append(chk('23a', f'{en} — 23a) Inv. total RF %',
                                               '% = widget 4 % RF entidad',
                                               '% RF entidad coincide con tabla activos',
                                               pct_rf, e_rf_pct, 'match_pct'))
                if rf_ent_t and e_rf_v is not None:
                    r_row = next((r for r in rf_ent_t if r.get('name') == en), None)
                    if r_row:
                        checks.append(chk('23a', f'{en} — 23a) RF entidad = widget 8',
                                           'RF entidad = entrada en tabla RF global (widget 8)',
                                           'Cross-check KPI RF entidad',
                                           r_row.get('value', 0), e_rf_v, 'match_value'))

            e_rf_prod = gd(ri, 'table_3')
            if e_rf_prod:
                checks.append(chk('24a', f'{en} — 24a) RF tipo producto', '% suma = 100%',
                                   'Suma % tipos producto RF entidad = 100%', None, pct_sum(e_rf_prod), 'pct100'))

            e_rf_em = gd(ri, 'chart_1')
            if e_rf_em:
                checks.append(chk('25a', f'{en} — 25a) RF emisor', '% suma = 100%',
                                   'Suma % tipos emisor RF entidad = 100%', None, pct_sum(e_rf_em), 'pct100'))
                for r in e_rf_em:
                    checks.append(chk('25a', f"{en} — 25a) RF emisor {r['name']}", 'Sin valores negativos',
                                       'Valores emisor RF entidad ≥ 0', None, r.get('value', 0), 'no_negative'))

            e_rf_rat = gd(ri, 'table_1')
            if e_rf_rat:
                checks.append(chk('26a', f'{en} — 26a) RF rating', '% suma = 100%',
                                   'Suma % ratings RF entidad = 100%', None, pct_sum(e_rf_rat), 'pct100'))
                if e_rf_v is not None:
                    checks.append(chk('26a', f'{en} — 26a) RF rating',
                                       'Σ importe = 23a inv. total RF entidad',
                                       'Suma importes ratings = KPI RF entidad',
                                       e_rf_v, val_sum(e_rf_rat), 'match_value'))

            e_rf_geo = gd(ri, 'chart_2')
            if e_rf_geo:
                checks.append(chk('27a', f'{en} — 27a) RF geografía', '% suma = 100%',
                                   'Suma % geografía RF entidad = 100%', None, pct_sum(e_rf_geo), 'pct100'))

            e_rf_venc = gd(ri, 'table_2')
            if e_rf_venc and val_sum(e_rf_venc) > 0:
                checks.append(chk('28a', f'{en} — 28a) RF vencimientos', '% suma = 100%',
                                   'Suma % vencimientos RF entidad = 100%', None, pct_sum(e_rf_venc), 'pct100'))

        if ent['rv_idx'] >= 0:
            ri = ent['rv_idx']
            e_rv_kpi = by_page(ri, 'kpi_list')
            e_rv_d = e_rv_kpi['content'].get('data') if e_rv_kpi else None
            e_rv_v = e_rv_d.get('value', e_rv_d) if isinstance(e_rv_d, dict) else e_rv_d

            if e_rv_kpi and dist_t:
                cr4 = next((c for c in dist_t if c.get('name') != 'total' and c.get('name') == en), None)
                if cr4:
                    rv_cell = next((d for d in (cr4.get('distribution') or []) if d.get('name') == 'equity'), None)
                    tot4 = next((d for d in (cr4.get('distribution') or []) if d.get('name') == 'total'), None)
                    if rv_cell:
                        checks.append(chk('29a', f'{en} — 29a) Inv. total RV',
                                           'Valor = widget 4 RV entidad',
                                           'KPI RV entidad = RV entidad en tabla global',
                                           rv_cell.get('value', 0), e_rv_v, 'match_value'))
                        if tot4 and tot4.get('value'):
                            pct_rv = rv_cell.get('value', 0) / tot4['value']
                            e_rv_pct = e_rv_d.get('percentage', 0) if isinstance(e_rv_d, dict) else 0
                            checks.append(chk('29a', f'{en} — 29a) Inv. total RV %',
                                               '% = widget 4 % RV entidad',
                                               '% RV entidad coincide con tabla activos',
                                               pct_rv, e_rv_pct, 'match_pct'))
                if rv_ent_t and e_rv_v is not None:
                    r_row = next((r for r in rv_ent_t if r.get('name') == en), None)
                    if r_row:
                        checks.append(chk('29a', f'{en} — 29a) RV entidad = widget 16',
                                           'RV entidad = entrada en tabla RV global (widget 16)',
                                           'Cross-check KPI RV entidad',
                                           r_row.get('value', 0), e_rv_v, 'match_value'))

            e_rv_geo = gd(ri, 'chart_bar_1')
            if e_rv_geo:
                checks.append(chk('30a', f'{en} — 30a) RV geografía', '% suma = 100%',
                                   'Suma % geografía RV entidad = 100%', None, pct_sum(e_rv_geo), 'pct100'))

            e_rv_sec = gd(ri, 'table_2')
            if e_rv_sec:
                checks.append(chk('31a', f'{en} — 31a) RV sector', '% suma = 100%',
                                   'Suma % sectores RV entidad = 100%', None, pct_sum(e_rv_sec), 'pct100'))
                if e_rv_v is not None:
                    checks.append(chk('31a', f'{en} — 31a) RV sector',
                                       'Σ importe = 29a inv. total RV entidad',
                                       'Suma importes sectores = KPI RV entidad',
                                       e_rv_v, val_sum(e_rv_sec), 'match_value'))

    # ── Scan genérico: porcentajes anómalos en cualquier widget ─────────────
    for key, w in jx['W'].items():
        items = _collect_pct_items(w['content'])
        if not items:
            continue
        pt = w.get('page_title', '')
        wid = w.get('widget', '')
        wtitle = w.get('wtitle', '') or wid
        group_label = f'{pt} — {wtitle}' if pt else wtitle
        c = _check_dist_rows(items, '—', group_label, wtitle, pt, wid)
        if c:
            checks.append(c)

    return checks
