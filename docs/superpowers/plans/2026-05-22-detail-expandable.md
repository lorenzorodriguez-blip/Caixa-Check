# Detail expandable en tabla de validación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cambiar el campo `detail` de los checks de `str` a `list[str]`, y mostrar un panel formateado debajo de la tabla de validación al seleccionar una fila con detalle.

**Architecture:** Tres cambios independientes y secuenciales: (1) `checks.py` produce listas en vez de strings concatenados, (2) `excel_export.py` une la lista antes de escribir la celda, (3) `app.py` activa selección de fila en el dataframe y renderiza el panel de detalle.

**Tech Stack:** Python 3.12, Streamlit ≥ 1.35, pandas ≥ 2.0

---

## Ficheros afectados

| Fichero | Cambio |
|---|---|
| `src/checks.py` | `chk()` retorna `detail: list[str]`; los checks CSV de calidad también usan lista |
| `src/excel_export.py` | `'\n'.join(c['detail'])` en vez de `c['detail']` directo |
| `app.py` | `st.dataframe` con `on_select`, panel de detalle debajo, columna `detail` quitada de la tabla |

---

## Task 1: Cambiar `detail` a `list[str]` en `checks.py`

**Files:**
- Modify: `src/checks.py`

La función `chk()` asigna `detail` como string en cinco sitios (uno por `mode`). Hay que convertirlos todos a lista. Además, los tres checks de calidad CSV que construyen `detail` directamente en `run_checks()` también usan el join — hay que convertirlos.

- [ ] **Step 1: Actualizar la función `chk()`**

Reemplaza el cuerpo completo de `chk()` (líneas 22–57 de `src/checks.py`) con:

```python
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
```

- [ ] **Step 2: Actualizar los tres checks de calidad CSV en `run_checks()`**

En `run_checks()` (líneas 82–110 de `src/checks.py`), hay tres bloques que construyen `detail` con un join. Cámbialos así:

**Bloque `unclassified` (≈ línea 83) — rama `if`:**
```python
# antes
detail = ' || '.join(fmt_row(r) for r in calcs['unclassified'].to_dict('records'))

# después
detail = [fmt_row(r) for r in calcs['unclassified'].to_dict('records')]
```

**Bloque `unclassified` — rama `else` (≈ línea 89), dentro del `checks.append`:**
```python
# antes
'detail': ''

# después
'detail': []
```

**Bloque `missing_ac` (≈ línea 97):**
```python
# antes
detail = ' || '.join(fmt_row(r) for r in calcs['missing_ac'].to_dict('records'))

# después
detail = [fmt_row(r) for r in calcs['missing_ac'].to_dict('records')]
```

**Bloque `missing_sac` (≈ línea 104):**
```python
# antes
detail = ' || '.join(fmt_row(r) for r in calcs['missing_sac'].to_dict('records'))

# después
detail = [fmt_row(r) for r in calcs['missing_sac'].to_dict('records')]
```

- [ ] **Step 3: Verificar que el módulo importa sin errores**

```bash
cd c:\Users\LorenzoRodriguez\Desktop\caixa-check
python -c "from src.checks import chk, run_checks; print('OK')"
```

Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/checks.py
git commit -m "refactor: change detail field from str to list[str] in checks"
```

---

## Task 2: Actualizar `excel_export.py`

**Files:**
- Modify: `src/excel_export.py:52`

- [ ] **Step 1: Cambiar la escritura del campo `detail` en la celda Excel**

En `build_excel()` (línea 52 de `src/excel_export.py`), dentro del bloque `for c in all_checks:`, la línea que escribe `c['detail']`:

```python
# antes (línea completa del row_data)
row_data = [c['odt'], c['group'], c['widget'], c['rule'],
            c['csv'], c['json'], c['status'].upper(), c['detail'],
            c.get('page_title', ''), c.get('widget_id', '')]

# después
row_data = [c['odt'], c['group'], c['widget'], c['rule'],
            c['csv'], c['json'], c['status'].upper(), '\n'.join(c['detail']),
            c.get('page_title', ''), c.get('widget_id', '')]
```

- [ ] **Step 2: Verificar que el módulo importa sin errores**

```bash
python -c "from src.excel_export import build_excel; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/excel_export.py
git commit -m "fix: join detail list before writing to Excel cell"
```

---

## Task 3: Actualizar `app.py` — selección de fila y panel de detalle

**Files:**
- Modify: `app.py`

La tabla actual muestra la columna `detail` (ilegible cuando es larga). El nuevo comportamiento: quitar `detail` de las columnas visibles de la tabla, activar selección de fila, y renderizar el panel debajo cuando la fila seleccionada tiene detalle.

- [ ] **Step 1: Cambiar el bloque de renderizado de la tabla de checks**

Localiza el bloque (≈ líneas 101–108 de `app.py`) que contiene:

```python
styled = df_checks[['odt', 'group', 'widget', 'rule', 'csv', 'json', 'status', 'detail']].style.map(
    _style_status, subset=['status']
)
st.dataframe(styled, use_container_width=True, hide_index=True)
```

Reemplázalo por:

```python
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
```

- [ ] **Step 2: Verificar que la app arranca sin errores de sintaxis**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Probar la app manualmente**

```bash
streamlit run app.py
```

Pasos de verificación:
1. Sube un CSV y un JSON en la pestaña **Validación** y ejecuta.
2. Confirma que la columna `detail` ya no aparece en la tabla.
3. Pincha una fila con estado `fail` que tenga activos problemáticos — debe aparecer el panel debajo con un bullet por activo.
4. Pincha una fila con estado `pass` (sin detalle) — no debe aparecer nada debajo.
5. Cambia el filtro a `Errores` — la selección se resetea y el panel desaparece.
6. Descarga el Excel y abre la hoja `Revisión` — la columna Δ debe mostrar el detalle como texto (separado por saltos de línea si hay varios items).

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: show detail panel on row selection in validation table"
```
