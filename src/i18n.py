"""Translation strings for the Caixa Check UI.

Usage: t("some.key", lang) -> the string in that language, with any
{placeholder} kwargs filled in. `lang` defaults to "es" so every existing
call site that doesn't pass a language keeps behaving exactly as before.
"""

STRINGS: dict[str, dict[str, str]] = {
    # ── diff.py ──────────────────────────────────────────────────────────
    "diff.period_a": {"es": "Periodo A", "en": "Period A"},
    "diff.period_b": {"es": "Periodo B", "en": "Period B"},
    "diff.page_fallback": {"es": "Pág {n}", "en": "Page {n}"},

    # NOTE: excel_export.py is NOT translated -- build_excel() always produces
    # the Spanish workbook regardless of the UI language toggle, by request.

    # ── app.py: _render_diff_summary / _render_asset_diff ───────────────
    "ui.total_metrics": {"es": "Total métricas", "en": "Total metrics"},
    "ui.changes_gt20": {"es": "Cambios >20%", "en": "Changes >20%"},
    "ui.changes_5_20": {"es": "Cambios 5-20%", "en": "Changes 5-20%"},
    "ui.changes_lt5": {"es": "Cambios <5%", "en": "Changes <5%"},
    "ui.col_metric": {"es": "Métrica", "en": "Metric"},
    "ui.col_variation": {"es": "Variación", "en": "Variation"},
    "ui.big_changes_header": {"es": "⚠ Cambios significativos (>20%)", "en": "⚠ Significant changes (>20%)"},
    "ui.medium_changes_header": {"es": "Cambios moderados (5–20%)", "en": "Moderate changes (5–20%)"},
    "ui.small_changes_header": {"es": "Cambios menores (<5%)", "en": "Minor changes (<5%)"},
    "ui.portfolio_detail_header": {"es": "Detalle de cartera — cambios por activo", "en": "Portfolio detail — changes by asset"},
    "ui.entries_expander": {"es": "🆕 Entradas — {n} activo(s) nuevo(s)", "en": "🆕 New positions — {n} new asset(s)"},
    "ui.col_asset": {"es": "Activo", "en": "Asset"},
    "ui.valuation_col": {"es": "Valoración ({date})", "en": "Valuation ({date})"},
    "ui.exits_expander": {"es": "❌ Salidas — {n} activo(s) que salieron", "en": "❌ Exited positions — {n} asset(s) that left"},
    "ui.value_changes_expander": {"es": "📊 Cambios en valoración — {n} activo(s)", "en": "📊 Valuation changes — {n} asset(s)"},

    # ── app.py: top-level tabs ────────────────────────────────────────────
    "ui.tab_validate": {"es": "Validación", "en": "Validation"},
    "ui.tab_diff": {"es": "Comparar periodos", "en": "Compare periods"},
    "ui.tab_repo": {"es": "Repositorio", "en": "Repository"},

    # ── app.py: Tab 1 — Validación ────────────────────────────────────────
    "ui.pdf_coming_soon": {"es": "📄 3. PDF — próximamente", "en": "📄 3. PDF — coming soon"},
    "ui.client_optional": {"es": "👤 Cliente (opcional)", "en": "👤 Client (optional)"},
    "ui.none_option": {"es": "— ninguno —", "en": "— none —"},
    "ui.caption_compare_prev": {"es": "Para comparar con periodo anterior", "en": "To compare with the previous period"},
    "ui.run_validation_btn": {"es": "▶ Ejecutar validación", "en": "▶ Run validation"},
    "ui.error_processing": {"es": "Error al procesar: {error}", "en": "Error processing: {error}"},
    "ui.total_checks": {"es": "Total checks", "en": "Total checks"},
    "ui.errors_metric": {"es": "✗ Errores", "en": "✗ Errors"},
    "ui.warnings_metric": {"es": "⚠ Advertencias", "en": "⚠ Warnings"},
    "ui.filter_label": {"es": "Filtrar:", "en": "Filter:"},
    "ui.filter_all": {"es": "Todos", "en": "All"},
    "ui.filter_errors": {"es": "Errores", "en": "Errors"},
    "ui.filter_warnings": {"es": "Advertencias", "en": "Warnings"},
    "ui.compare_prev_subheader": {"es": "Comparar con periodo anterior", "en": "Compare with previous period"},
    "ui.prev_period_found": {"es": "Periodo anterior encontrado: {date}", "en": "Previous period found: {date}"},
    "ui.compare_btn": {"es": "▶ Comparar", "en": "▶ Compare"},
    "ui.preparing_excel": {"es": "Preparando Excel…", "en": "Preparing Excel…"},
    "ui.download_excel_btn": {"es": "📥 Descargar Excel", "en": "📥 Download Excel"},

    # ── app.py: Tab 2 — Comparar periodos ─────────────────────────────────
    "ui.subtab_from_repo": {"es": "📁 Desde repositorio", "en": "📁 From repository"},
    "ui.subtab_upload": {"es": "⬆ Subir archivos", "en": "⬆ Upload files"},
    "ui.client_label": {"es": "Cliente", "en": "Client"},
    "ui.period_b_current": {"es": "Periodo B — Actual", "en": "Period B — Current"},
    "ui.no_saved_reports": {"es": "Sin reportes guardados", "en": "No saved reports"},
    "ui.period_a_previous": {"es": "Periodo A — Anterior", "en": "Period A — Previous"},
    "ui.no_previous_periods": {"es": "Sin periodos anteriores disponibles", "en": "No previous periods available"},
    "ui.compare_periods_btn": {"es": "▶ Comparar periodos", "en": "▶ Compare periods"},
    "ui.load_report_error": {"es": "No se pudo cargar uno de los reportes del repositorio.", "en": "Could not load one of the reports from the repository."},
    "ui.error_comparing": {"es": "Error al comparar: {error}", "en": "Error comparing: {error}"},
    "ui.json_previous": {"es": "JSON Anterior", "en": "Previous JSON"},
    "ui.json_current": {"es": "JSON Actual", "en": "Current JSON"},

    # ── app.py: Tab 3 — Repositorio ────────────────────────────────────────
    "ui.add_client_expander": {"es": "+ Añadir nuevo cliente", "en": "+ Add new client"},
    "ui.client_id_label": {"es": "ID del cliente (UUID)", "en": "Client ID (UUID)"},
    "ui.add_client_btn": {"es": "Añadir cliente", "en": "Add client"},
    "ui.client_added": {"es": "Cliente añadido: {id}", "en": "Client added: {id}"},
    "ui.client_exists": {"es": "Ese cliente ya existe.", "en": "That client already exists."},
    "ui.invalid_id": {"es": "Introduce un ID válido.", "en": "Enter a valid ID."},
    "ui.save_report_subheader": {"es": "Guardar reporte", "en": "Save report"},
    "ui.report_json_label": {"es": "JSON del reporte", "en": "Report JSON"},
    "ui.excel_optional_label": {"es": "Excel (opcional)", "en": "Excel (optional)"},
    "ui.report_date_label": {"es": "Fecha del reporte", "en": "Report date"},
    "ui.save_report_btn": {"es": "💾 Guardar reporte", "en": "💾 Save report"},
    "ui.report_saved": {"es": "Reporte guardado ({label}) — {client} / {date}", "en": "Report saved ({label}) — {client} / {date}"},
    "ui.no_prev_report_info": {"es": "No hay reporte anterior guardado para este cliente. La comparación estará disponible la próxima semana.", "en": "No previous report saved for this client yet. The comparison will be available next week."},
    "ui.error_saving": {"es": "Error al guardar: {error}", "en": "Error saving: {error}"},
    "ui.error_deleting": {"es": "Error al eliminar: {error}", "en": "Error deleting: {error}"},
    "ui.comparison_header": {"es": "Comparación: {a} vs {b}", "en": "Comparison: {a} vs {b}"},
    "ui.report_history_subheader": {"es": "Historial de reportes", "en": "Report history"},
    "ui.no_reports_yet": {"es": "No hay reportes guardados aún.", "en": "No reports saved yet."},
    "ui.delete_report_subheader": {"es": "Eliminar reporte", "en": "Delete report"},
    "ui.no_reports_for_client": {"es": "Sin reportes para este cliente", "en": "No reports for this client"},
    "ui.delete_report_btn": {"es": "🗑 Eliminar reporte", "en": "🗑 Delete report"},
    "ui.date_label": {"es": "Fecha", "en": "Date"},
    "ui.delete_confirm_warning": {
        "es": "¿Seguro? Se eliminarán el JSON y el Excel (si existe) de **{client}** / **{date}**. Esta acción no se puede deshacer.",
        "en": "Are you sure? This will delete the JSON and Excel (if any) for **{client}** / **{date}**. This action cannot be undone.",
    },
    "ui.confirm_delete_btn": {"es": "Confirmar eliminación", "en": "Confirm deletion"},
    "ui.report_deleted": {"es": "Reporte eliminado — {client} / {date}", "en": "Report deleted — {client} / {date}"},

    # ── app.py: Tab 3 report-history table columns (renamed for display only;
    #    src/repository.py's dict keys ('cliente'/'fecha'/'excel') are untouched) ──
    "ui.col_client": {"es": "cliente", "en": "client"},
    "ui.col_date": {"es": "fecha", "en": "date"},
    "ui.col_excel": {"es": "excel", "en": "excel"},
}


def t(key: str, lang: str = "es", **kwargs) -> str:
    """Look up `key` in `lang`, formatting in any kwargs. Raises KeyError
    (loudly, on purpose) if the key or language doesn't exist — a missing
    translation should fail fast in review/testing, not ship silently."""
    return STRINGS[key][lang].format(**kwargs)
