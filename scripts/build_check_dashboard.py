"""Build the Caixa Check dashboard HTML from a scripts/batch_check.py JSON result.

Usage:
    python scripts/build_check_dashboard.py <batch_check_output.json> <out.html> "<run timestamp>" [<clients.json>]

<clients.json> is optional -- when given, client UUIDs not listed in it are
tagged with a "NEW" badge, same convention as the Caixa Drift dashboard.
"""
import html
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = Path(sys.argv[1])
OUT_PATH = Path(sys.argv[2])
RUN_TIMESTAMP = sys.argv[3]
CLIENTS_PATH = Path(sys.argv[4]) if len(sys.argv) > 4 else None

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
clients = data["clients"]
e = html.escape

known_clients = set()
if CLIENTS_PATH and CLIENTS_PATH.exists():
    known_clients = set(json.loads(CLIENTS_PATH.read_text(encoding="utf-8")))


def pill(label, kind):
    return f'<span class="pill pill-{kind}"><i class="dot"></i>{e(label)}</span>'


def new_badge(uid):
    if not known_clients or uid in known_clients:
        return ""
    return ' <span class="new-badge">NEW — not in clients.json</span>'


ok = {u: r for u, r in clients.items() if "error" not in r}
errored = {u: r for u, r in clients.items() if "error" in r}

failing = {u: r for u, r in ok.items() if r.get("fail", 0) > 0}
warn_only = {u: r for u, r in ok.items() if r.get("fail", 0) == 0 and r.get("warn", 0) > 0}
clean = {u: r for u, r in ok.items() if r.get("fail", 0) == 0 and r.get("warn", 0) == 0}


# ── Per-client cards (unchanged shape from previous manually-authored runs) ──

def issue_rows_html(issues):
    out = []
    for c in issues:
        detail = "<br>".join(e(d) for d in c.get("detail", []))
        out.append(f"""
        <tr class="issue-row issue-{c['status']}">
          <td>{pill(c['status'].upper(), c['status'])}</td>
          <td>
            <div class="issue-group">{e(c['group'])}</div>
            <div class="issue-rule">{e(c['rule'])}</div>
          </td>
          <td class="mono nowrap">{e(c['csv'])}</td>
          <td class="mono nowrap">{e(c['json'])}</td>
          <td class="issue-detail">{detail}</td>
        </tr>""")
    return "\n".join(out)


def client_card(uid, r):
    kind = "fail" if r.get("fail", 0) > 0 else "warn"
    return f"""
    <details class="client-card client-{kind}" open>
      <summary>
        <span class="client-id">{e(uid)}</span>{new_badge(uid)}
        <span class="summary-counts"><span class="cnt cnt-fail">{r['fail']} fail</span> · <span class="cnt cnt-warn">{r['warn']} warn</span> · <span class="cnt cnt-pass">{r['pass']} pass</span> <span class="cnt-total">/ {r['total']} checks</span></span>
      </summary>
      <div class="client-body">
        <table class="issue-table">
          <thead><tr><th>Status</th><th>Check</th><th>CSV</th><th>JSON</th><th>Detail</th></tr></thead>
          <tbody>{issue_rows_html(r.get("issues", []))}</tbody>
        </table>
      </div>
    </details>"""


def clean_row(uid, r):
    return f"""<li class="clean-row"><span class="pill pill-pass"><i class="dot"></i>PASS</span><span class="client-id">{e(uid)}</span>{new_badge(uid)}<span class="clean-count">{r['pass']}/{r['total']} checks passed</span></li>"""


def skipped_row(uid, r):
    return f"""<li class="skipped-row"><span class="pill pill-error"><i class="dot"></i>ERROR</span><span class="client-id">{e(uid)}</span>{new_badge(uid)}<span class="skipped-reason">{e(r.get('error', ''))}</span></li>"""


# ── Cross-client issue-type dropdowns (new) ──────────────────────────────────

def stale_price_rows(rows):
    out = []
    for r in sorted(rows, key=lambda r: -r.get("days_stale", 0)):
        sev = r.get("severity", "warn")
        out.append(f"""
        <tr class="issue-row issue-{sev}">
          <td>{pill(sev.upper(), sev)}</td>
          <td class="mono nowrap">{e(r.get('isin', '—'))}</td>
          <td>{e(r.get('asset_description', r.get('raw', '—')))}</td>
          <td class="mono nowrap">{e(r.get('last_price_date', '—'))}</td>
          <td class="mono nowrap num">{e(str(r.get('days_stale', '—')))}</td>
          <td class="client-id">{e(r['client'])}</td>
        </tr>""")
    return "\n".join(out)


def simple_rows(rows):
    out = []
    for r in rows:
        out.append(f"""
        <tr>
          <td class="mono nowrap">{e(r.get('isin', '—'))}</td>
          <td>{e(r.get('asset_description', r.get('raw', '—')))}</td>
          <td>{e(r.get('custodian', '—'))}</td>
          <td class="mono nowrap num">{e(str(r.get('market_value', '—')))}</td>
          <td class="client-id">{e(r['client'])}</td>
        </tr>""")
    return "\n".join(out)


def classification_rows(rows):
    out = []
    for r in rows:
        missing = []
        if not r.get("asset_class_group"):
            missing.append("asset_class_group")
        if not r.get("sub_asset_class"):
            missing.append("sub_asset_class")
        sev = r.get("severity", "warn")
        out.append(f"""
        <tr class="issue-row issue-{sev}">
          <td>{pill(sev.upper(), sev)}</td>
          <td class="mono nowrap">{e(r.get('isin', '—'))}</td>
          <td>{e(r.get('asset_description', r.get('raw', '—')))}</td>
          <td>{e(r.get('custodian', '—'))}</td>
          <td class="mono nowrap num">{e(str(r.get('market_value', '—')))}</td>
          <td class="mono">{e(' + '.join(missing) or '—')}</td>
          <td class="client-id">{e(r['client'])}</td>
        </tr>""")
    return "\n".join(out)


def cross_dropdown(title, count_label, headers, rows_html, empty_msg):
    if not rows_html:
        body = f'<p class="section-sub">{empty_msg}</p>'
    else:
        head = "".join(f"<th>{h}</th>" for h in headers)
        body = f'<table class="issue-table"><thead><tr>{head}</tr></thead><tbody>{rows_html}</tbody></table>'
    return f"""
    <details class="client-card">
      <summary>
        <span class="client-id">{e(title)}</span>
        <span class="summary-counts">{e(count_label)}</span>
      </summary>
      <div class="client-body">{body}</div>
    </details>"""


stale_prices_all = data.get("stale_prices_all", [])
fi_rating_all = data.get("fi_missing_rating_all", [])
funds_alloc_all = data.get("funds_missing_allocation_all", [])
classification_all = data.get("classification_issues_all", [])

stale_clients = {r["client"] for r in stale_prices_all}
rating_clients = {r["client"] for r in fi_rating_all}
alloc_clients = {r["client"] for r in funds_alloc_all}
classification_clients = {r["client"] for r in classification_all}

cross_dropdowns_html = "".join([
    cross_dropdown(
        "ISINs with stale/missing prices",
        f"{len(stale_prices_all)} asset(s) across {len(stale_clients)} client(s)",
        ["Sev", "ISIN", "Asset", "Last price", "Days stale", "Client"],
        stale_price_rows(stale_prices_all),
        "No stale prices this run.",
    ),
    cross_dropdown(
        "Fixed income with no credit rating",
        f"{len(fi_rating_all)} asset(s) across {len(rating_clients)} client(s)",
        ["ISIN", "Asset", "Custodian", "Market value", "Client"],
        simple_rows(fi_rating_all),
        "No bonds/money-market assets missing a credit rating this run.",
    ),
    cross_dropdown(
        "Funds with no allocation datapoint",
        f"{len(funds_alloc_all)} fund(s) across {len(alloc_clients)} client(s)",
        ["ISIN", "Asset", "Custodian", "Market value", "Client"],
        simple_rows(funds_alloc_all),
        "No funds missing an allocation breakdown this run.",
    ),
    cross_dropdown(
        "Assets with incomplete classification",
        f"{len(classification_all)} asset(s) across {len(classification_clients)} client(s)",
        ["Sev", "ISIN", "Asset", "Custodian", "Market value", "Missing", "Client"],
        classification_rows(classification_all),
        "No assets missing asset_class_group/sub_asset_class this run.",
    ),
])

failing_html = "\n".join(client_card(u, r) for u, r in sorted(failing.items(), key=lambda kv: -kv[1]["fail"]))
warn_html = "\n".join(client_card(u, r) for u, r in warn_only.items())
clean_html = "\n".join(clean_row(u, r) for u, r in clean.items())
skipped_html = "\n".join(skipped_row(u, r) for u, r in errored.items())

HTML = f"""<title>Caixa Check</title>
<style>
:root {{
  --page: #f9f9f7;
  --surface: #fcfcfb;
  --ink: #0b0b0b;
  --ink-secondary: #52514e;
  --ink-muted: #898781;
  --hairline: #e1e0d9;
  --border: rgba(11,11,11,0.10);
  --accent: #4a3aa7;
  --accent-soft: #ece9f7;
  --good: #0ca30c;
  --good-soft: #e3f5e3;
  --warning: #fab219;
  --warning-soft: #fdf1da;
  --critical: #d03b3b;
  --critical-soft: #fbe6e6;
  --serious: #ec835a;
  --serious-soft: #fdece4;
  --font-display: 'Fraunces', Georgia, serif;
  --font-ui: 'IBM Plex Sans', system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, "SF Mono", Consolas, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-secondary: #c3c2b7;
    --ink-muted: #92908a; --hairline: #2c2c2a; --border: rgba(255,255,255,0.12);
    --accent: #9085e9; --accent-soft: #241f47; --good-soft: #123312;
    --warning-soft: #3a2c0d; --critical-soft: #3a1a1a; --serious-soft: #3a2418;
  }}
}}
:root[data-theme="dark"] {{
  --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-secondary: #c3c2b7;
  --ink-muted: #92908a; --hairline: #2c2c2a; --border: rgba(255,255,255,0.12);
  --accent: #9085e9; --accent-soft: #241f47; --good-soft: #123312;
  --warning-soft: #3a2c0d; --critical-soft: #3a1a1a; --serious-soft: #3a2418;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  background: var(--page); color: var(--ink); font-family: var(--font-ui);
  font-size: 15px; line-height: 1.5; -webkit-font-smoothing: antialiased;
}}
.page {{ max-width: 980px; margin: 0 auto; padding: 56px 24px 100px; display: flex; flex-direction: column; gap: 40px; }}
.masthead {{ display: flex; flex-direction: column; gap: 6px; }}
.eyebrow {{
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--accent); font-weight: 600;
}}
h1 {{ font-family: var(--font-display); font-weight: 600; font-size: 40px; margin: 0; text-wrap: balance; }}
.subtitle {{ color: var(--ink-secondary); font-size: 14px; }}
.subtitle .mono {{ font-family: var(--font-mono); }}
.stats {{
  display: grid; grid-template-columns: repeat(5, 1fr); gap: 1px; background: var(--hairline);
  border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden;
}}
.tile {{ background: var(--surface); padding: 18px 16px; display: flex; flex-direction: column; gap: 4px; border-top: 3px solid transparent; }}
.tile-value {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; font-size: 28px; font-weight: 600; color: var(--ink); }}
.tile-label {{ font-size: 12px; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.06em; }}
.tile-fail {{ border-top-color: var(--critical); }}
.tile-warn {{ border-top-color: var(--warning); }}
.tile-clean {{ border-top-color: var(--good); }}
.tile-err {{ border-top-color: var(--serious); }}
section {{ display: flex; flex-direction: column; gap: 14px; }}
.section-head {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }}
.section-head h2 {{ font-family: var(--font-display); font-size: 22px; margin: 0; }}
.section-sub {{ color: var(--ink-muted); font-size: 13px; }}
.pill {{
  display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; letter-spacing: 0.04em; padding: 3px 8px; border-radius: 999px; white-space: nowrap;
}}
.pill .dot {{ width: 7px; height: 7px; border-radius: 50%; display: inline-block; }}
.pill-fail {{ background: var(--critical-soft); color: var(--ink); }} .pill-fail .dot {{ background: var(--critical); }}
.pill-warn {{ background: var(--warning-soft); color: var(--ink); }} .pill-warn .dot {{ background: var(--warning); }}
.pill-pass {{ background: var(--good-soft); color: var(--ink); }} .pill-pass .dot {{ background: var(--good); }}
.pill-error {{ background: var(--serious-soft); color: var(--ink); }} .pill-error .dot {{ background: var(--serious); }}
.new-badge {{
  font-family: var(--font-mono); font-size: 10px; font-weight: 600; letter-spacing: 0.04em;
  background: var(--accent-soft); color: var(--accent); padding: 2px 7px; border-radius: 999px;
}}
.client-card {{ background: var(--surface); border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden; }}
.client-card + .client-card {{ margin-top: 10px; }}
.client-card summary {{ cursor: pointer; list-style: none; padding: 14px 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
.client-card summary::-webkit-details-marker {{ display: none; }}
.client-card summary::before {{ content: '▸'; color: var(--ink-muted); font-size: 12px; transition: transform 0.15s ease; }}
.client-card[open] summary::before {{ transform: rotate(90deg); }}
.client-id {{ font-family: var(--font-mono); font-size: 13px; font-weight: 600; }}
.summary-counts {{ font-size: 12px; color: var(--ink-secondary); margin-left: auto; }}
.cnt {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
.cnt-fail {{ color: var(--ink); font-weight: 600; }}
.cnt-warn {{ color: var(--ink); font-weight: 600; }}
.cnt-pass {{ color: var(--ink-secondary); }}
.cnt-total {{ color: var(--ink-muted); }}
.client-card[open] {{ border-color: var(--border); }}
.client-fail {{ border-left: 3px solid var(--critical); }}
.client-warn {{ border-left: 3px solid var(--warning); }}
.client-body {{ border-top: 1px solid var(--hairline); overflow-x: auto; }}
table.issue-table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 640px; }}
table.issue-table th {{
  text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--ink-muted); font-weight: 600; padding: 10px 14px; border-bottom: 1px solid var(--hairline);
}}
table.issue-table td {{ padding: 10px 14px; border-bottom: 1px solid var(--hairline); vertical-align: top; }}
table.issue-table tr:last-child td {{ border-bottom: none; }}
.issue-group {{ font-weight: 600; }}
.issue-rule {{ color: var(--ink-muted); font-size: 12px; margin-top: 2px; }}
.issue-detail {{ color: var(--ink-secondary); font-size: 12.5px; }}
.mono {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
.nowrap {{ white-space: nowrap; }}
.num {{ text-align: right; }}
.clean-list {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }}
.clean-row {{
  display: flex; align-items: center; gap: 10px; background: var(--surface); border: 1px solid var(--hairline);
  border-radius: 8px; padding: 10px 14px; font-size: 13px; flex-wrap: wrap;
}}
.clean-count {{ color: var(--ink-muted); margin-left: auto; font-size: 12px; }}
.skipped-list {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }}
.skipped-row {{
  display: flex; align-items: center; gap: 10px; background: var(--surface); border: 1px solid var(--hairline);
  border-radius: 8px; padding: 10px 14px; font-size: 13px; flex-wrap: wrap;
}}
.skipped-reason {{ color: var(--ink-muted); margin-left: auto; font-size: 12px; font-family: var(--font-mono); }}
footer {{ border-top: 1px solid var(--hairline); padding-top: 20px; font-size: 12px; color: var(--ink-muted); display: flex; flex-direction: column; gap: 4px; }}
@media (max-width: 720px) {{ .stats {{ grid-template-columns: repeat(2, 1fr); }} h1 {{ font-size: 30px; }} }}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="page">

  <div class="masthead">
    <div class="eyebrow">GlobalView validation · tramoia</div>
    <h1>Caixa Check</h1>
    <div class="subtitle">
      <span class="mono">{len(clients)}</span> clients checked · run <span class="mono">{e(RUN_TIMESTAMP)}</span> · only "ready" tramoia reports processed
    </div>
  </div>

  <div class="stats">
    <div class="tile tile-total"><div class="tile-value">{len(clients)}</div><div class="tile-label">Clients checked</div></div>
    <div class="tile tile-fail"><div class="tile-value">{len(failing)}</div><div class="tile-label">Failing</div></div>
    <div class="tile tile-warn"><div class="tile-value">{len(warn_only)}</div><div class="tile-label">Warnings only</div></div>
    <div class="tile tile-clean"><div class="tile-value">{len(clean)}</div><div class="tile-label">Clean</div></div>
    <div class="tile tile-err"><div class="tile-value">{len(errored)}</div><div class="tile-label">Pipeline errors</div></div>
  </div>

  <section>
    <div class="section-head">
      <h2>Cross-client issues</h2>
      <div class="section-sub">Same data-quality signal grouped across every client — click to expand</div>
    </div>
    {cross_dropdowns_html}
  </section>

  <section>
    <div class="section-head">
      <h2>Needs attention</h2>
      <div class="section-sub">{len(failing)} client(s) with at least one failing check</div>
    </div>
    {failing_html if failing_html else '<p class="section-sub">None this run.</p>'}
  </section>

  <section>
    <div class="section-head">
      <h2>Warnings only</h2>
      <div class="section-sub">{len(warn_only)} client(s) with warnings but nothing failing</div>
    </div>
    {warn_html if warn_html else '<p class="section-sub">None this run.</p>'}
  </section>

  <section>
    <div class="section-head">
      <h2>Clean</h2>
      <div class="section-sub">{len(clean)} client(s), all checks passing</div>
    </div>
    <ul class="clean-list">{clean_html if clean_html else '<li class="section-sub">None.</li>'}</ul>
  </section>

  <section>
    <div class="section-head">
      <h2>Pipeline errors</h2>
      <div class="section-sub">{len(errored)} client(s) whose CSV/JSON couldn't even be parsed — a pipeline problem, not a data-quality finding</div>
    </div>
    <ul class="skipped-list">{skipped_html if skipped_html else '<li class="section-sub">None — every client&#39;s files parsed cleanly.</li>'}</ul>
  </section>

  <footer>
    <div>Source: tramoia (Flanks internal) — GlobalView positions report, most recent "ready" report per client.</div>
    <div>Clients marked NEW were found on tramoia but are not yet in this repo's data/clients.json — add them there if they should be tracked going forward.</div>
    <div>Client data lives only in this private artifact and the gitignored <span class="mono">data/</span> folder — never committed.</div>
  </footer>

</div>
"""

OUT_PATH.write_text(HTML, encoding="utf-8")
print("wrote", OUT_PATH, len(HTML), "bytes")
print("failing:", len(failing), "warn_only:", len(warn_only), "clean:", len(clean), "errored:", len(errored))
print("cross-client: stale_prices", len(stale_prices_all), "| fi_rating", len(fi_rating_all),
      "| funds_alloc", len(funds_alloc_all), "| classification", len(classification_all))
