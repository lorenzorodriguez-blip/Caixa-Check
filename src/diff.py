def extract_metrics(data: dict) -> dict:
    pages = data.get('pages', [])
    metrics: dict = {}
    for i, page in enumerate(pages):
        pt = (page.get('layout') or {}).get('title', '') or f'Pág {i}'
        for w in page.get('widgets', []):
            content = w.get('content') or []
            if not content:
                continue
            c = content[0]
            wn = w.get('name', '')
            key = f"{i}_{w.get('id') or w.get('name')}"
            label = f"{pt} › {w.get('title') or w.get('id') or wn}"

            if wn == 'kpi_list':
                d = c.get('data')
                v = d.get('value', d) if isinstance(d, dict) else d
                if isinstance(v, (int, float)) and v != 0:
                    metrics[key] = {'label': label, 'value': float(v)}

            if wn == 'kpi_box':
                d = c.get('data')
                if isinstance(d, (int, float)) and d != 0:
                    metrics[f"{key}_{w.get('title', '')}"] = {
                        'label': f"{pt} › {w.get('title', '')}",
                        'value': float(d),
                    }

            if wn in ('table', 'table_full_distributions'):
                tot = c.get('total')
                if tot and tot != 0:
                    metrics[f'{key}_tot'] = {'label': f'{label} (total)', 'value': float(tot)}

            if wn in ('chart_bar_distribution', 'currency_distribution_chart'):
                tot = c.get('total')
                if tot and tot != 0:
                    metrics[f'{key}_tot'] = {'label': f'{label} (total)', 'value': float(tot)}

    return metrics


def run_diff(data_a: dict, data_b: dict) -> list:
    m_a = extract_metrics(data_a)
    m_b = extract_metrics(data_b)

    date_a = (((data_a.get('pages') or [{}])[3:4] or [{}])[0]
               .get('widgets', [{}])[0:1] or [{}])[0]
    date_a = ((date_a.get('content') or [{}])[0:1] or [{}])[0].get('date', 'Periodo A')

    date_b = (((data_b.get('pages') or [{}])[3:4] or [{}])[0]
               .get('widgets', [{}])[0:1] or [{}])[0]
    date_b = ((date_b.get('content') or [{}])[0:1] or [{}])[0].get('date', 'Periodo B')

    diffs = []
    for k in set(m_a) | set(m_b):
        a, b = m_a.get(k), m_b.get(k)
        if not a or not b:
            continue
        abs_diff = abs(b['value'] - a['value'])
        pct_diff = ((b['value'] - a['value']) / abs(a['value']) * 100) if a['value'] != 0 else None
        sev = 'small'
        if pct_diff is not None:
            sev = 'big' if abs(pct_diff) > 20 else 'medium' if abs(pct_diff) > 5 else 'small'
        diffs.append({
            'label':    a.get('label') or b.get('label'),
            'val_a':    a['value'],
            'val_b':    b['value'],
            'abs_diff': abs_diff,
            'pct_diff': pct_diff,
            'sev':      sev,
            'date_a':   date_a,
            'date_b':   date_b,
        })

    diffs.sort(key=lambda d: ({'big': 0, 'medium': 1, 'small': 2}[d['sev']], -d['abs_diff']))
    return diffs
