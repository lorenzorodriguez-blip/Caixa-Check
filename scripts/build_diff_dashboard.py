"""Build the Caixa Drift (period-comparison) dashboard HTML from a
scripts/batch_diff.py JSON result.

Usage:
    python scripts/build_diff_dashboard.py <batch_diff_output.json> <out.html> "<run timestamp>"
"""
import html
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA_PATH = Path(sys.argv[1])
OUT_PATH = Path(sys.argv[2])
RUN_TIMESTAMP = sys.argv[3]

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
clients = data["clients"]
e = html.escape


def fmt_eur(v):
    try:
        return f"{v:,.0f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v:+.1f}%"


def big_count(r):
    return r.get("metric_severity", {}).get("big", 0) + r.get("asset_severity", {}).get("big", 0)


ok = {u: r for u, r in clients.items() if "error" not in r}
errored = {u: r for u, r in clients.items() if "error" in r}
diffed = {u: r for u, r in ok.items() if r.get("previous_date")}
no_prev = {u: r for u, r in ok.items() if not r.get("previous_date")}

big_movers = sorted(
    [(u, r) for u, r in diffed.items() if big_count(r) > 0],
    key=lambda item: -big_count(item[1]),
)
quiet = [(u, r) for u, r in diffed.items() if big_count(r) == 0]

total_new = sum(len(r.get("asset_new", [])) for r in diffed.values())
total_removed = sum(len(r.get("asset_removed", [])) for r in diffed.values())

period_label = ""
if diffed:
    sample = next(iter(diffed.values()))
    period_label = f'{sample["previous_date"]} → {sample["report_date"]}'


def pill(label, kind):
    return f'<span class="pill pill-{kind}"><i class="dot"></i>{e(label)}</span>'


def metric_rows_html(diffs, limit=None):
    rows = diffs if limit is None else diffs[:limit]
    out = []
    for d in rows:
        out.append(f"""
        <tr>
          <td>{pill(d['sev'].upper(), d['sev'])}</td>
          <td class="issue-group">{e(d['label'])}</td>
          <td class="mono nowrap num">{fmt_eur(d['val_a'])}</td>
          <td class="mono nowrap num">{fmt_eur(d['val_b'])}</td>
          <td class="mono nowrap num">{fmt_pct(d['pct_diff'])}</td>
        </tr>""")
    return "\n".join(out)


def asset_rows_html(rows, status):
    out = []
    for d in rows:
        val = fmt_eur(d["val_b"]) if status == "new" else fmt_eur(d["val_a"]) if status == "removed" else None
        if status == "changed":
            row = f"""
        <tr>
          <td>{pill(d['sev'].upper(), d['sev'])}</td>
          <td>{e(d['name'])}<div class="issue-rule mono">{e(d['isin'])}</div></td>
          <td class="mono nowrap num">{fmt_eur(d['val_a'])}</td>
          <td class="mono nowrap num">{fmt_eur(d['val_b'])}</td>
          <td class="mono nowrap num">{fmt_pct(d['pct_diff'])}</td>
        </tr>"""
        else:
            row = f"""
        <tr>
          <td>{pill('NEW' if status == 'new' else 'EXIT', 'good' if status == 'new' else 'fail')}</td>
          <td>{e(d['name'])}<div class="issue-rule mono">{e(d['isin'])}</div></td>
          <td class="mono nowrap num">{val}</td>
        </tr>"""
        out.append(row)
    return "\n".join(out)


def client_card(uid, r):
    md = sorted(r.get("metric_diffs", []), key=lambda d: ({"big": 0, "medium": 1, "small": 2}[d["sev"]], -d["abs_diff"]))
    md_big_medium = [d for d in md if d["sev"] in ("big", "medium")]
    new_a = r.get("asset_new", [])
    rem_a = r.get("asset_removed", [])
    chg_a_big = [d for d in r.get("asset_changed", []) if d["sev"] == "big"]

    parts = []
    if md_big_medium:
        parts.append(f"""
        <table class="issue-table">
          <thead><tr><th>Sev</th><th>Metric</th><th>{e(r['previous_date'])}</th><th>{e(r['report_date'])}</th><th>Δ%</th></tr></thead>
          <tbody>{metric_rows_html(md_big_medium, limit=10)}</tbody>
        </table>""")
    if new_a or rem_a or chg_a_big:
        asset_body = ""
        if new_a:
            asset_body += f'<table class="issue-table"><thead><tr><th>Status</th><th>Asset</th><th>Value</th></tr></thead><tbody>{asset_rows_html(new_a, "new")}</tbody></table>'
        if rem_a:
            asset_body += f'<table class="issue-table"><thead><tr><th>Status</th><th>Asset</th><th>Value</th></tr></thead><tbody>{asset_rows_html(rem_a, "removed")}</tbody></table>'
        if chg_a_big:
            asset_body += f'<table class="issue-table"><thead><tr><th>Sev</th><th>Asset</th><th>{e(r["previous_date"])}</th><th>{e(r["report_date"])}</th><th>Δ%</th></tr></thead><tbody>{asset_rows_html(chg_a_big, "changed")}</tbody></table>'
        parts.append(asset_body)

    body = "".join(f'<div class="client-body">{p}</div>' for p in parts)
    n_big = big_count(r)
    return f"""
    <details class="client-card client-fail" open>
      <summary>
        <span class="client-id">{e(uid)}</span>
        <span class="summary-counts"><span class="cnt cnt-fail">{n_big} big move(s)</span> · <span class="cnt cnt-pass">{len(new_a)} new / {len(rem_a)} exited asset(s)</span></span>
      </summary>
      {body}
    </details>"""


def quiet_row(uid, r):
    return f"""
    <li class="clean-row">
      <span class="pill pill-pass"><i class="dot"></i>STABLE</span>
      <span class="client-id">{e(uid)}</span>
      <span class="clean-count">{r['metric_severity']['small']} small change(s), nothing bigger</span>
    </li>"""


def no_prev_row(uid, r):
    return f"""
    <li class="clean-row">
      <span class="pill pill-warn"><i class="dot"></i>FIRST</span>
      <span class="client-id">{e(uid)}</span>
      <span class="clean-count">archived {e(r['report_date'])} — no prior period to compare yet</span>
    </li>"""


big_movers_html = "\n".join(client_card(u, r) for u, r in big_movers)
quiet_html = "\n".join(quiet_row(u, r) for u, r in quiet)
no_prev_html = "\n".join(no_prev_row(u, r) for u, r in no_prev.items())

HTML = f"""<title>Caixa Drift</title>
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
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--hairline);
  border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden;
}}
.tile {{ background: var(--surface); padding: 18px 16px; display: flex; flex-direction: column; gap: 4px; border-top: 3px solid transparent; }}
.tile-value {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; font-size: 28px; font-weight: 600; color: var(--ink); }}
.tile-label {{ font-size: 12px; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.06em; }}
.tile-fail {{ border-top-color: var(--critical); }}
.tile-good {{ border-top-color: var(--good); }}
.tile-warn {{ border-top-color: var(--warning); }}
section {{ display: flex; flex-direction: column; gap: 14px; }}
.section-head {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }}
.section-head h2 {{ font-family: var(--font-display); font-size: 22px; margin: 0; }}
.section-sub {{ color: var(--ink-muted); font-size: 13px; }}
.pill {{
  display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 11px;
  font-weight: 600; letter-spacing: 0.04em; padding: 3px 8px; border-radius: 999px; white-space: nowrap;
}}
.pill .dot {{ width: 7px; height: 7px; border-radius: 50%; display: inline-block; }}
.pill-big {{ background: var(--critical-soft); color: var(--ink); }} .pill-big .dot {{ background: var(--critical); }}
.pill-medium {{ background: var(--warning-soft); color: var(--ink); }} .pill-medium .dot {{ background: var(--warning); }}
.pill-small {{ background: var(--accent-soft); color: var(--ink); }} .pill-small .dot {{ background: var(--accent); }}
.pill-good {{ background: var(--good-soft); color: var(--ink); }} .pill-good .dot {{ background: var(--good); }}
.pill-fail {{ background: var(--critical-soft); color: var(--ink); }} .pill-fail .dot {{ background: var(--critical); }}
.pill-warn {{ background: var(--warning-soft); color: var(--ink); }} .pill-warn .dot {{ background: var(--warning); }}
.pill-pass {{ background: var(--good-soft); color: var(--ink); }} .pill-pass .dot {{ background: var(--good); }}
.client-card {{ background: var(--surface); border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden; }}
.client-card + .client-card {{ margin-top: 10px; }}
.client-card summary {{ cursor: pointer; list-style: none; padding: 14px 16px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
.client-card summary::-webkit-details-marker {{ display: none; }}
.client-card summary::before {{ content: '▸'; color: var(--ink-muted); font-size: 12px; transition: transform 0.15s ease; }}
.client-card[open] summary::before {{ transform: rotate(90deg); }}
.client-id {{ font-family: var(--font-mono); font-size: 13px; font-weight: 600; }}
.summary-counts {{ font-size: 12px; color: var(--ink-secondary); margin-left: auto; }}
.cnt {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
.cnt-fail {{ color: var(--ink); font-weight: 600; }}
.cnt-pass {{ color: var(--ink-secondary); }}
.client-fail {{ border-left: 3px solid var(--critical); }}
.client-body {{ border-top: 1px solid var(--hairline); overflow-x: auto; }}
table.issue-table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 560px; }}
table.issue-table th {{
  text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-muted);
  font-weight: 600; padding: 10px 14px; border-bottom: 1px solid var(--hairline);
}}
table.issue-table td {{ padding: 9px 14px; border-bottom: 1px solid var(--hairline); vertical-align: top; }}
table.issue-table tr:last-child td {{ border-bottom: none; }}
.issue-group {{ font-weight: 600; }}
.issue-rule {{ color: var(--ink-muted); font-size: 11.5px; margin-top: 2px; }}
.mono {{ font-family: var(--font-mono); font-variant-numeric: tabular-nums; }}
.nowrap {{ white-space: nowrap; }}
.num {{ text-align: right; }}
.clean-list {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }}
.clean-row {{
  display: flex; align-items: center; gap: 12px; background: var(--surface); border: 1px solid var(--hairline);
  border-radius: 8px; padding: 10px 14px; font-size: 13px;
}}
.clean-count {{ color: var(--ink-muted); margin-left: auto; font-size: 12px; }}
footer {{ border-top: 1px solid var(--hairline); padding-top: 20px; font-size: 12px; color: var(--ink-muted); display: flex; flex-direction: column; gap: 4px; }}
@media (max-width: 720px) {{ .stats {{ grid-template-columns: repeat(2, 1fr); }} h1 {{ font-size: 30px; }} }}
</style>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<div class="page">
  <div class="masthead">
    <div class="eyebrow">Period comparison · tramoia</div>
    <h1>Caixa Drift</h1>
    <div class="subtitle">
      <span class="mono">{len(diffed)}</span> clients compared ({e(period_label)}) ·
      <span class="mono">{len(no_prev)}</span> newly archived · run <span class="mono">{RUN_TIMESTAMP}</span>
    </div>
  </div>

  <div class="stats">
    <div class="tile tile-fail">
      <div class="tile-value">{len(big_movers)}</div>
      <div class="tile-label">Clients with big moves</div>
    </div>
    <div class="tile tile-good">
      <div class="tile-value">{total_new}</div>
      <div class="tile-label">New positions opened</div>
    </div>
    <div class="tile tile-warn">
      <div class="tile-value">{total_removed}</div>
      <div class="tile-label">Positions exited</div>
    </div>
    <div class="tile">
      <div class="tile-value">{len(quiet)}</div>
      <div class="tile-label">Stable clients</div>
    </div>
  </div>

  <section>
    <div class="section-head">
      <h2>Big moves</h2>
      <div class="section-sub">{len(big_movers)} client(s) with a &gt;20% swing in a metric or position</div>
    </div>
    {big_movers_html if big_movers else '<p class="section-sub">None this period.</p>'}
  </section>

  <section>
    <div class="section-head">
      <h2>Stable</h2>
      <div class="section-sub">{len(quiet)} client(s), only small period-over-period changes</div>
    </div>
    <ul class="clean-list">{quiet_html if quiet else '<li class="section-sub">None.</li>'}</ul>
  </section>

  <section>
    <div class="section-head">
      <h2>Newly archived</h2>
      <div class="section-sub">{len(no_prev)} client(s) with no earlier period stored yet</div>
    </div>
    <ul class="clean-list">{no_prev_html if no_prev else '<li class="section-sub">None.</li>'}</ul>
  </section>

  <footer>
    <div>Source: tramoia (Flanks internal) — GlobalView positions report, archived into data/reports/ per client per date.</div>
    <div>Severity: big &gt;20% change, medium 5–20%, small &lt;5% (same thresholds as the Caixa Check app's "Comparar periodos" tab).</div>
  </footer>
</div>
"""

OUT_PATH.write_text(HTML, encoding="utf-8")
print("wrote", OUT_PATH, len(HTML), "bytes")
print("big movers:", [u for u, _ in big_movers])
print("quiet:", len(quiet), "no_prev:", len(no_prev))
