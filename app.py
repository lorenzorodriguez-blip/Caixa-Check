import json
from datetime import date

import pandas as pd
import streamlit as st

from src.calcs import build_calcs, extract_json
from src.checks import run_checks
from src.diff import run_diff
from src.excel_export import build_excel
from src.parser import parse_csv

st.set_page_config(
    page_title='Caixa Check',
    page_icon='🏦',
    layout='wide',
)

st.title('Caixa Check')

tab_validate, tab_diff = st.tabs(['Validación', 'Comparar periodos'])

# ── Tab 1: Validación ────────────────────────────────────────────────────────
with tab_validate:
    col1, col2, col3 = st.columns(3)
    with col1:
        csv_file = st.file_uploader('📊 1. CSV Input', type=['csv'], key='csv')
    with col2:
        json_file = st.file_uploader('{ } 2. JSON', type=['json'], key='json')
    with col3:
        st.info('📄 3. PDF — próximamente')

    run_disabled = not (csv_file and json_file)
    run_clicked = st.button('▶ Ejecutar validación', disabled=run_disabled, type='primary')

    if run_clicked:
        try:
            csv_text = csv_file.read().decode('utf-8')
            json_data = json.loads(json_file.read().decode('utf-8'))
            df = parse_csv(csv_text)
            calcs = build_calcs(df)
            jx = extract_json(json_data)
            checks = run_checks(calcs, jx)
            st.session_state['checks'] = checks
            st.session_state['df'] = df
            st.session_state['json_data'] = json_data
        except Exception as e:
            st.error(f'Error al procesar: {e}')

    if 'checks' in st.session_state:
        checks = st.session_state['checks']
        n_total = len(checks)
        n_pass  = sum(1 for c in checks if c['status'] == 'pass')
        n_fail  = sum(1 for c in checks if c['status'] == 'fail')
        n_warn  = sum(1 for c in checks if c['status'] == 'warn')

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Total checks', n_total)
        m2.metric('✓ OK', n_pass)
        m3.metric('✗ Errores', n_fail, delta=f'-{n_fail}' if n_fail else None, delta_color='inverse')
        m4.metric('⚠ Advertencias', n_warn)

        filter_opt = st.radio('Filtrar:', ['Todos', 'Errores', 'Advertencias', 'OK'],
                              horizontal=True, key='filter_validate')

        df_checks = pd.DataFrame(checks)
        filter_map = {'Errores': 'fail', 'Advertencias': 'warn', 'OK': 'pass'}
        if filter_opt in filter_map:
            df_checks = df_checks[df_checks['status'] == filter_map[filter_opt]]

        def _style_status(val):
            colors = {'pass': 'color:#42f5b3', 'warn': 'color:#f5a742', 'fail': 'color:#f54260'}
            return colors.get(val, '')

        styled = df_checks[['odt', 'group', 'widget', 'rule', 'csv', 'json', 'status', 'detail']].style.map(
            _style_status, subset=['status']
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # Excel download
        with st.spinner('Preparando Excel…'):
            excel_bytes = build_excel(st.session_state['df'], st.session_state['json_data'])
        filename = f"CaixaCheck_{date.today().strftime('%Y%m%d')}.xlsx"
        st.download_button(
            '📥 Descargar Excel',
            data=excel_bytes,
            file_name=filename,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

# ── Tab 2: Comparar periodos ─────────────────────────────────────────────────
with tab_diff:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown('**Periodo A — Anterior**')
        json_a_file = st.file_uploader('JSON Anterior', type=['json'], key='json_a')
    with col_b:
        st.markdown('**Periodo B — Actual**')
        json_b_file = st.file_uploader('JSON Actual', type=['json'], key='json_b')

    diff_disabled = not (json_a_file and json_b_file)
    diff_clicked = st.button('▶ Comparar periodos', disabled=diff_disabled, type='primary')

    if diff_clicked:
        try:
            j_a = json.loads(json_a_file.read().decode('utf-8'))
            j_b = json.loads(json_b_file.read().decode('utf-8'))
            diffs = run_diff(j_a, j_b)
            st.session_state['diffs'] = diffs
        except Exception as e:
            st.error(f'Error al comparar: {e}')

    if 'diffs' in st.session_state:
        diffs = st.session_state['diffs']
        date_a = diffs[0]['date_a'] if diffs else 'Periodo A'
        date_b = diffs[0]['date_b'] if diffs else 'Periodo B'

        big  = [d for d in diffs if d['sev'] == 'big']
        med  = [d for d in diffs if d['sev'] == 'medium']
        sml  = [d for d in diffs if d['sev'] == 'small']

        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Total métricas', len(diffs))
        m2.metric('Cambios >20%', len(big))
        m3.metric('Cambios 5-20%', len(med))
        m4.metric('Cambios <5%', len(sml))

        def _render_diff_table(items, label):
            if not items:
                return
            st.subheader(label)
            df_d = pd.DataFrame([{
                'Métrica':    d['label'],
                date_a:       d['val_a'],
                date_b:       d['val_b'],
                'Variación':  d['val_b'] - d['val_a'],
                '%':          f"{d['pct_diff']:+.1f}%" if d['pct_diff'] is not None else '—',
            } for d in items])
            st.dataframe(df_d, use_container_width=True, hide_index=True)

        _render_diff_table(big, '⚠ Cambios significativos (>20%)')
        _render_diff_table(med, 'Cambios moderados (5–20%)')
        _render_diff_table(sml, 'Cambios menores (<5%)')
