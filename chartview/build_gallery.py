"""Build the static viewport gallery (METHODOLOGY §0b #149/#159).

One self-contained HTML page per (ticker, setup date):
  - bare OHLC+Volume chart first (no item picked),
  - picker list of READY recipes (charts in page order),
  - DISABLED / DO_NOT_DRAW entries rendered as greyed text with blocker reasons,
    never drawn (#159: no guessing).

Usage:
  python3 -m chartview.build_gallery --data SPY.parquet --ticker SPY \
      --setups 2021-11-12 2022-06-15 --out gallery_out
"""
import argparse
import html
import os

from chartview import data as D
from chartview import render as R
from chartview.recipes import PICKER, DO_NOT_DRAW_STATIC, READY, DISABLED

CSS = """
body { font-family: -apple-system, 'Segoe UI', Arial, sans-serif; margin: 24px auto; max-width: 1180px; color: #1f2430; }
h1 { font-size: 20px; } h2 { font-size: 16px; margin-top: 34px; }
.picker { border: 1px solid #c9c3d6; border-radius: 8px; padding: 12px 16px; background: #faf9fc; }
.picker ul { margin: 6px 0; padding-left: 20px; }
.picker .disabled { color: #9aa0ad; }
.picker .reason { font-size: 12px; }
.chart { border: 1px solid #e3e0ea; border-radius: 8px; margin-top: 12px; }
.note { color: #667; font-size: 12px; }
a { color: #7e22ce; }
"""


def _picker_html():
    out = ['<div class="picker"><b>Checklist picker</b> (READY items drawn below in order; disabled items are never drawn)<ul>']
    for rid, desc, _fn in PICKER:
        out.append(f'<li><b>{html.escape(rid)}</b> — {html.escape(desc)}</li>')
    for rid, why in DO_NOT_DRAW_STATIC:
        out.append(f'<li class="disabled"><b>{html.escape(rid)}</b> — DO_NOT_DRAW: <span class="reason">{html.escape(why)}</span></li>')
    out.append('</ul></div>')
    return '\n'.join(out)


def build_page(df, ticker, setup, outdir):
    dates, O, H, L, C, V, cutoff = D.as_of(df, setup)
    setup_ts = str(setup)[:10]
    parts = [f'<html><head><meta charset="utf-8"><title>{ticker} viewport {setup_ts}</title>',
             f'<style>{CSS}</style></head><body>',
             f'<h1>{ticker} — TradingView-style viewport gallery — setup date {setup_ts}</h1>',
             '<p class="note">Only data knowable at the setup date\'s open is used: cutoff bar = last '
             'completed daily bar with candle end &lt; setup date; day-S OHLCV never read. '
             'Purple = highlighted bars/lines/zones (#149/#153/#155). One reading per definition (#156).</p>',
             _picker_html(),
             '<h2>BARE — OHLC + Volume (no item picked)</h2>']

    # bare chart
    fig = R.make_figure(dates, O, H, L, C, V, cutoff, 'BARE', 'OHLC + Volume only', '', [],
                        ticker=ticker)
    parts.append('<div class="chart">' + fig.to_html(full_html=False, include_plotlyjs='inline') + '</div>')

    # one section per recipe
    for rid, desc, fn in PICKER:
        res = fn(dates, O, H, L, C, V, cutoff)
        parts.append(f'<h2 id="{rid}">{html.escape(rid)} <span class="note">— {html.escape(desc)}</span></h2>')
        if res['status'] == DISABLED:
            parts.append(f'<p class="picker"><span class="disabled"><b>DISABLED</b> — '
                         f'<span class="reason">{html.escape(res["blocker"])}</span></span></p>')
            continue
        fig = R.make_figure(dates, O, H, L, C, V, cutoff, rid, res['label'], res['answer'],
                            res['ops'], ticker=ticker)
        parts.append('<div class="chart">' + fig.to_html(full_html=False, include_plotlyjs=False) + '</div>')

    parts.append('</body></html>')
    path = os.path.join(outdir, f'{ticker}_{setup_ts}.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(parts))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--ticker', required=True)
    ap.add_argument('--setups', nargs='+', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    df = D.load_daily(a.data)
    made = []
    for s in a.setups:
        made.append(build_page(df, a.ticker, s, a.out))
    idx = ['<html><head><meta charset="utf-8"><title>viewport gallery index</title></head><body>',
           f'<h1>{a.ticker} viewport gallery</h1><ul>']
    for p in made:
        b = os.path.basename(p)
        idx.append(f'<li><a href="{b}">{b}</a></li>')
    idx.append('</ul></body></html>')
    ipath = os.path.join(a.out, 'index.html')
    with open(ipath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(idx))
    print('wrote', ipath, 'and', len(made), 'page(s)')


if __name__ == '__main__':
    main()
