import json
from datetime import date

import pandas as pd
import streamlit as st

from src.calcs import build_calcs, extract_json
from src.checks import run_checks
from src.diff import run_diff, run_asset_diff
from src.excel_export import build_excel
from src.parser import parse_csv
from src.repository import add_client, delete_report, get_previous_report, list_all_reports, load_clients, load_report, list_reports, save_report

st.set_page_config(
    page_title='Caixa Check',
    page_icon='🏦',
    layout='wide',
)

st.title('Caixa Check')


def _render_diff_summary(diffs: list, date_a: str, date_b: str) -> None:
    big = [d for d in diffs if d['sev'] == 'big']
    med = [d for d in diffs if d['sev'] == 'medium']
    sml = [d for d in diffs if d['sev'] == 'small']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Total métricas', len(diffs))
    m2.metric('Cambios >20%', len(big))
    m3.metric('Cambios 5-20%', len(med))
    m4.metric('Cambios <5%', len(sml))

    def _table(items, label):
        if not items:
            return
        st.subheader(label)
        st.dataframe(pd.DataFrame([{
            'Métrica':   d['label'],
            date_a:      d['val_a'],
            date_b:      d['val_b'],
            'Variación': d['val_b'] - d['val_a'],
            '%':         f"{d['pct_diff']:+.1f}%" if d['pct_diff'] is not None else '—',
        } for d in items]), use_container_width=True, hide_index=True)

    _table(big, '⚠ Cambios significativos (>20%)')
    _table(med, 'Cambios moderados (5–20%)')
    _table(sml, 'Cambios menores (<5%)')


def _style_pct(val: str) -> str:
    if val == '—':
        return ''
    try:
        v = float(str(val).replace('%', '').replace('+', ''))
        if abs(v) > 20:
            return 'color:#f54260'
        if abs(v) > 5:
            return 'color:#f5a742'
        return 'color:#42f5b3'
    except ValueError:
        return ''


def _render_asset_diff(asset_diffs: list, date_a: str, date_b: str) -> None:
    if not asset_diffs:
        return

    new     = [d for d in asset_diffs if d['status'] == 'new']
    removed = [d for d in asset_diffs if d['status'] == 'removed']
    changed = [d for d in asset_diffs if d['status'] == 'changed']

    if not (new or removed or changed):
        return

    st.subheader('Detalle de cartera — cambios por activo')

    if new:
        with st.expander(f'🆕 Entradas — {len(new)} activo(s) nuevo(s)', expanded=False):
            st.dataframe(pd.DataFrame([{
                'Activo': d['name'], 'ISIN': d['isin'],
                f'Valoración ({date_b})': d['val_b'],
            } for d in new]), use_container_width=True, hide_index=True)

    if removed:
        with st.expander(f'❌ Salidas — {len(removed)} activo(s) que salieron', expanded=False):
            st.dataframe(pd.DataFrame([{
                'Activo': d['name'], 'ISIN': d['isin'],
                f'Valoración ({date_a})': d['val_a'],
            } for d in removed]), use_container_width=True, hide_index=True)

    if changed:
        with st.expander(f'📊 Cambios en valoración — {len(changed)} activo(s)', expanded=False):
            df_ch = pd.DataFrame([{
                'Activo': d['name'],
                'ISIN': d['isin'],
                date_a: d['val_a'],
                date_b: d['val_b'],
                'Δ': d['val_b'] - d['val_a'],
                '%': f"{d['pct_diff']:+.1f}%" if d['pct_diff'] is not None else '—',
            } for d in changed])
            styled = df_ch.style.map(_style_pct, subset=['%'])
            st.dataframe(styled, use_container_width=True, hide_index=True)


tab_validate, tab_diff, tab_repo = st.tabs(['Validación', 'Comparar periodos', 'Repositorio'])

# ── Tab 1: Validación ────────────────────────────────────────────────────────
with tab_validate:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        csv_file = st.file_uploader('📊 1. CSV Input', type=['csv'], key='csv')
    with col2:
        json_file = st.file_uploader('{ } 2. JSON', type=['json'], key='json')
    with col3:
        st.info('📄 3. PDF — próximamente')
    with col4:
        val_client = st.selectbox(
            '👤 Cliente (opcional)',
            ['— ninguno —'] + load_clients(),
            key='val_client',
        )
        st.caption('Para comparar con periodo anterior')

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

        display_cols = ['odt', 'group', 'widget', 'rule', 'csv', 'json', 'status']
        styled = df_checks[display_cols].style.map(_style_status, subset=['status'])
        event = st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            on_select='rerun',
            selection_mode='single-row',
        )

        selected_rows = event.selection.get('rows', [])
        if selected_rows:
            idx = selected_rows[0]
            row = df_checks.iloc[idx]
            items = row['detail'] or []
            if items:
                st.divider()
                st.markdown(f"**{row['group']}** / *{row['rule']}*")
                if len(items) == 1:
                    st.markdown(items[0])
                else:
                    st.markdown('\n'.join(f'- {item}' for item in items))

        # ── Comparación con periodo anterior ────────────────────────────────
        if val_client != '— ninguno —':
            prev = get_previous_report(val_client, date.today())
            if prev:
                prev_date, prev_data = prev
                st.divider()
                st.subheader('Comparar con periodo anterior')
                st.caption(f'Periodo anterior encontrado: {prev_date}')
                if st.button('▶ Comparar', key='btn_val_diff', type='primary'):
                    val_diffs = run_diff(prev_data, st.session_state['json_data'])
                    st.session_state['val_diffs'] = val_diffs
                    st.session_state['val_diff_dates'] = (str(prev_date), str(date.today()))
                    st.session_state['val_asset_diffs'] = run_asset_diff(prev_data, st.session_state['json_data'])

        if 'val_diffs' in st.session_state:
            date_a, date_b = st.session_state['val_diff_dates']
            _render_diff_summary(st.session_state['val_diffs'], date_a, date_b)
            _render_asset_diff(st.session_state.get('val_asset_diffs', []), date_a, date_b)

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
    subtab_repo, subtab_upload = st.tabs(['📁 Desde repositorio', '⬆ Subir archivos'])

    with subtab_repo:
        rd_col1, rd_col2, rd_col3 = st.columns(3)
        with rd_col1:
            diff_client = st.selectbox('Cliente', load_clients(), key='diff_client')
        dates = list_reports(diff_client)
        with rd_col3:
            if len(dates) >= 1:
                diff_date_b = st.selectbox(
                    'Periodo B — Actual',
                    options=list(reversed(dates)),
                    key='diff_date_b',
                )
            else:
                diff_date_b = None
                st.caption('Sin reportes guardados')
        with rd_col2:
            dates_a = [d for d in dates if diff_date_b and d < diff_date_b]
            if dates_a:
                diff_date_a = st.selectbox(
                    'Periodo A — Anterior',
                    options=list(reversed(dates_a)),
                    key='diff_date_a',
                )
            else:
                diff_date_a = None
                st.caption('Sin periodos anteriores disponibles')

        repo_diff_ok = diff_date_a is not None and diff_date_b is not None
        if st.button('▶ Comparar periodos', disabled=not repo_diff_ok,
                     type='primary', key='btn_repo_diff'):
            try:
                j_a = load_report(diff_client, diff_date_a)
                j_b = load_report(diff_client, diff_date_b)
                if j_a is None or j_b is None:
                    st.error('No se pudo cargar uno de los reportes del repositorio.')
                else:
                    diffs = run_diff(j_a, j_b)
                    st.session_state['diffs'] = diffs
                    st.session_state['diff_dates'] = (str(diff_date_a), str(diff_date_b))
                    st.session_state['asset_diffs'] = run_asset_diff(j_a, j_b)
            except Exception as e:
                st.error(f'Error al comparar: {e}')

    with subtab_upload:
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('**Periodo A — Anterior**')
            json_a_file = st.file_uploader('JSON Anterior', type=['json'], key='json_a')
        with col_b:
            st.markdown('**Periodo B — Actual**')
            json_b_file = st.file_uploader('JSON Actual', type=['json'], key='json_b')

        diff_disabled = not (json_a_file and json_b_file)
        diff_clicked = st.button('▶ Comparar periodos', disabled=diff_disabled,
                                 type='primary', key='btn_upload_diff')

        if diff_clicked:
            try:
                j_a = json.loads(json_a_file.read().decode('utf-8'))
                j_b = json.loads(json_b_file.read().decode('utf-8'))
                diffs = run_diff(j_a, j_b)
                st.session_state['diffs'] = diffs
                st.session_state.pop('diff_dates', None)
                st.session_state['asset_diffs'] = run_asset_diff(j_a, j_b)
            except Exception as e:
                st.error(f'Error al comparar: {e}')

    if 'diffs' in st.session_state:
        diffs = st.session_state['diffs']
        if 'diff_dates' in st.session_state:
            date_a, date_b = st.session_state['diff_dates']
        else:
            date_a = diffs[0]['date_a'] if diffs else 'Periodo A'
            date_b = diffs[0]['date_b'] if diffs else 'Periodo B'
        _render_diff_summary(diffs, date_a, date_b)
        _render_asset_diff(st.session_state.get('asset_diffs', []), date_a, date_b)

# ── Tab 3: Repositorio ───────────────────────────────────────────────────────
with tab_repo:
    # Añadir nuevo cliente
    with st.expander('+ Añadir nuevo cliente'):
        new_client_id = st.text_input('ID del cliente (UUID)', key='new_client_id')
        if st.button('Añadir cliente', key='btn_add_client'):
            if new_client_id.strip():
                added = add_client(new_client_id.strip())
                if added:
                    st.success(f'Cliente añadido: {new_client_id.strip()}')
                    st.rerun()
                else:
                    st.warning('Ese cliente ya existe.')
            else:
                st.error('Introduce un ID válido.')

    st.subheader('Guardar reporte')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        repo_json_file = st.file_uploader('JSON del reporte', type=['json'], key='repo_json')
    with col2:
        repo_excel_file = st.file_uploader('Excel (opcional)', type=['xlsx'], key='repo_excel')
    with col3:
        repo_client = st.selectbox('Cliente', load_clients(), key='repo_client')
    with col4:
        repo_date = st.date_input('Fecha del reporte', value=date.today(), key='repo_date')

    save_clicked = st.button('💾 Guardar reporte', disabled=not repo_json_file, type='primary')

    if save_clicked and repo_json_file:
        try:
            repo_json_data = json.loads(repo_json_file.read().decode('utf-8'))
            excel_bytes = repo_excel_file.read() if repo_excel_file else None
            save_report(repo_client, repo_date, repo_json_data, excel_bytes)
            label = 'JSON + Excel' if excel_bytes else 'JSON'
            st.success(f'Reporte guardado ({label}) — {repo_client} / {repo_date}')

            prev = get_previous_report(repo_client, repo_date)
            if prev:
                prev_date, prev_data = prev
                repo_diffs = run_diff(prev_data, repo_json_data)
                st.session_state['repo_diffs'] = repo_diffs
                st.session_state['repo_diff_dates'] = (str(prev_date), str(repo_date))
                st.session_state['repo_asset_diffs'] = run_asset_diff(prev_data, repo_json_data)
            else:
                st.session_state.pop('repo_diffs', None)
                st.info('No hay reporte anterior guardado para este cliente. La comparación estará disponible la próxima semana.')
        except Exception as e:
            st.error(f'Error al guardar: {e}')

    if 'repo_diffs' in st.session_state:
        date_a, date_b = st.session_state['repo_diff_dates']
        st.divider()
        st.subheader(f'Comparación: {date_a} vs {date_b}')
        _render_diff_summary(st.session_state['repo_diffs'], date_a, date_b)
        _render_asset_diff(st.session_state.get('repo_asset_diffs', []), date_a, date_b)

    st.divider()
    st.subheader('Historial de reportes')
    all_reports = list_all_reports()
    if all_reports:
        st.dataframe(pd.DataFrame(all_reports), use_container_width=True, hide_index=True)
    else:
        st.info('No hay reportes guardados aún.')

    st.divider()
    st.subheader('Eliminar reporte')
    if st.session_state.get('del_success'):
        st.success(st.session_state.pop('del_success'))
    if not all_reports:
        st.info('No hay reportes guardados aún.')
    else:
        del_col1, del_col2 = st.columns(2)
        with del_col1:
            del_client = st.selectbox(
                'Cliente', load_clients(), key='del_client',
                on_change=lambda: st.session_state.pop('del_confirm', None),
            )
        del_dates = list_reports(del_client)
        with del_col2:
            if del_dates:
                del_date = st.selectbox(
                    'Fecha',
                    options=list(reversed(del_dates)),
                    format_func=lambda d: d.strftime('%Y-%m-%d'),
                    key='del_date',
                )
            else:
                del_date = None
                st.caption('Sin reportes para este cliente')

        if st.button('🗑 Eliminar reporte', disabled=del_date is None,
                     type='secondary', key='btn_del'):
            st.session_state['del_confirm'] = True

        if st.session_state.get('del_confirm') and del_date is not None:
            st.warning(
                f'¿Seguro? Se eliminarán el JSON y el Excel (si existe) de '
                f'**{del_client}** / **{del_date}**. Esta acción no se puede deshacer.'
            )
            if st.button('Confirmar eliminación', type='primary', key='btn_del_confirm'):
                try:
                    delete_report(del_client, del_date)
                    st.session_state.pop('del_confirm', None)
                    st.session_state['del_success'] = f'Reporte eliminado — {del_client} / {del_date}'
                    st.rerun()
                except Exception as e:
                    st.session_state.pop('del_confirm', None)
                    st.error(f'Error al eliminar: {e}')
