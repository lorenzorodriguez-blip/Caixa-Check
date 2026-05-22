# Detail expandable en tabla de validación

**Fecha:** 2026-05-22
**Rama:** EX1

## Problema

El campo `detail` de los checks de validación puede contener muchos activos concatenados con `||`. En la tabla actual (`st.dataframe`) el texto queda truncado y no es legible.

## Objetivo

Permitir al usuario leer el contenido completo del campo `detail` de cualquier check que lo tenga, sin salir de la tabla de resultados.

## Decisiones de diseño

- **Visualización:** tabla Streamlit con selección de fila (A2). Al pinchar una fila con detalle, aparece un panel formateado justo debajo de la tabla.
- **Filas sin detalle:** si la fila seleccionada tiene `detail` vacío, no se muestra nada. No hay mensaje ni panel.
- **Estructura de datos:** `detail` pasa de `str` a `list[str]` en toda la cadena (Enfoque 1). Más limpio que parsear el string en el UI y elimina el riesgo de split frágil.

## Cambios por fichero

### `src/checks.py`

La función `chk()` cambia el tipo de retorno de `detail` de `str` a `list[str]`:

| Caso actual | Nuevo valor |
|---|---|
| `''` (sin detalle) | `[]` |
| `f'Δ {fmt(d)}'` (un solo valor) | `[f'Δ {fmt(d)}']` |
| `' \|\| '.join(fmt_row(r) for r in rows)` | `[fmt_row(r) for r in rows]` |

El formato de cada item producido por `fmt_row()` no cambia:
```
TELEFONICA SA | ISIN: ES0178430E18 | BBVA | MV: 12.345 € | asset_class: "" | sub_asset: ""
```

### `src/excel_export.py`

Una sola línea cambia en `build_excel()`, donde se escribe `c['detail']` en la celda Excel:

```python
# antes
c['detail']

# después
'\n'.join(c['detail'])
```

### `app.py`

En el bloque de la pestaña **Validación**, el `st.dataframe` pasa a tener selección de fila:

```python
event = st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
)
```

Justo debajo, se renderiza el panel de detalle condicionalmente:

```python
selected_rows = event.selection.get("rows", [])
if selected_rows:
    idx = selected_rows[0]
    row = df_checks.iloc[idx]
    items = row["detail"] or []
    if items:
        st.markdown(f"**{row['group']}** / {row['rule']}")
        if len(items) == 1:
            st.markdown(items[0])
        else:
            st.markdown("\n".join(f"- {item}" for item in items))
```

## Comportamiento esperado

1. El usuario ejecuta la validación y ve la tabla de checks.
2. Pincha una fila con estado `fail` que tiene activos sin clasificar.
3. Debajo de la tabla aparece un panel con el nombre del check y un bullet por cada activo afectado.
4. Pincha otra fila con estado `pass` (sin detalle) — el panel desaparece o no aparece nada.
5. Cambia el filtro (`Errores / Advertencias / OK`) — la selección se resetea naturalmente.

## Ficheros que NO cambian

- `src/parser.py`
- `src/calcs.py`
- `src/diff.py`
- `src/market_data.py`
- `src/repository.py`
- `src/constants.py`

## Tests

No hay suite de tests automatizados en el proyecto. La verificación es manual: ejecutar la app con un CSV y JSON de prueba y confirmar que el panel aparece y desaparece correctamente al seleccionar filas.
