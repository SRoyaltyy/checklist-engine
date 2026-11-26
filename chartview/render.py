"""Plotly renderer for viewport recipes: bare OHLC+Volume panes with purple highlights,
cutoff marker and a label box naming the measured quantity (METHODOLOGY §0b #149-#159).

Static HTML: build_gallery.py writes self-contained pages (plotly.js inline once per page).
The renderer never sees bars after the cutoff — run_ticker-style no-lookahead is enforced by
the caller passing arrays truncated at cutoff.
"""
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PURPLE = '#a855f7'
PURPLE_DK = '#7e22ce'
PURPLE_BAND = 'rgba(168,85,247,0.10)'
PURPLE_SHADE = 'rgba(168,85,247,0.16)'
RED, GREEN, DOJI = '#ef4444', '#22c55e', '#9ca3af'
CUT = '#0ea5e9'


def _bar_colours(O, C, purple):
    col = np.where(C < O, RED, np.where(C > O, GREEN, DOJI))
    col[list(purple)] = PURPLE
    return col


def _runs(idx, col):
    """split bar indices into maximal runs of identical colour -> [(indices, colour)]."""
    if not len(idx):
        return []
    out = []
    s = 0
    for k in range(1, len(idx)):
        if col[idx[k]] != col[idx[k - 1]]:
            out.append((idx[s:k], col[idx[k - 1]]))
            s = k
    out.append((idx[s:], col[idx[-1]]))
    return out


def make_figure(dates, O, H, L, C, V, cutoff, recipe_id, label, answer, ops,
                show_bars=140, ticker='', binary=None):
    """dates/O/H/L/C/V truncated at cutoff inclusive. All ops in bar-index space.

    binary: None | list of {'qid', 'q', 'a'} — strict YES/NO derived questions
    (§0b 2026-10-29 22:51/23:05). None = feature blank/switched off -> rendered
    as NOT_EVALUABLE, never silently NO.
    """
    dates = np.asarray(dates)
    n = len(dates)
    i0 = max(0, n - show_bars)
    xs = dates[i0:n]
    rng = np.arange(i0, n)

    purple_c = set()
    purple_v = set()
    shapes = []
    hlines, dots, polylines = [], [], []

    for op in ops:
        k = op['op']
        if k == 'recolour':
            purple_c.update(int(i) for i in op['bars'])
        elif k == 'recolour_vol':
            purple_v.update(int(i) for i in op['bars'])
        elif k == 'vband':
            shapes.append(dict(type='rect', xref='x', yref='paper', x0=op['i0'] - 0.5,
                               x1=op['i1'] + 0.5, y0=0, y1=1, fillcolor=PURPLE_BAND, line_width=0,
                               layer='below'))
        elif k == 'shade_between':
            shapes.append(dict(type='rect', xref='paper', yref='y', x0=0, x1=1,
                               y0=min(op['p0'], op['p1']), y1=max(op['p0'], op['p1']),
                               fillcolor=PURPLE_SHADE, line_width=0, layer='below'))
        elif k == 'hlines':
            hlines.extend(op['levels'])
        elif k == 'dots':
            dots.append(op['pts'])
        elif k == 'polyline':
            polylines.append(op['pts'])
        else:
            raise ValueError(f'unknown op {k}')

    col = _bar_colours(O, C, purple_c)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22],
                        vertical_spacing=0.02)

    for idx_run, c in _runs(list(rng), col):
        fig.add_trace(go.Candlestick(
            x=dates[idx_run], open=O[idx_run], high=H[idx_run], low=L[idx_run], close=C[idx_run],
            increasing_line_color=c, decreasing_line_color=c,
            increasing_fillcolor=c, decreasing_fillcolor=c,
            line_width=1.2, name='price', showlegend=False), row=1, col=1)

    # volume bars: purple for recolour_vol, else candle colour rule
    vcol = np.where(np.isin(rng, list(purple_v)), PURPLE,
                    np.where(C[rng] < O[rng], RED, np.where(C[rng] > O[rng], GREEN, DOJI)))
    fig.add_trace(go.Bar(x=xs, y=V[rng], marker_color=vcol, name='volume', showlegend=False),
                  row=2, col=1)

    # ops overlays
    for price, lab in hlines:
        fig.add_trace(go.Scatter(x=[xs[0], xs[-1]], y=[price, price], mode='lines',
                                 line=dict(color=PURPLE_DK, width=1.2, dash='dot'),
                                 name=lab, showlegend=False,
                                 hovertext=f'{lab}: {price:.6g}', hoverinfo='text'), row=1, col=1)
        fig.add_annotation(x=xs[-1], y=price, text=lab, showarrow=False, yshift=8,
                           font=dict(size=9, color=PURPLE_DK), xanchor='right', row=1, col=1)
    for pts in dots:
        if pts:
            fig.add_trace(go.Scatter(x=dates[[p[0] for p in pts]], y=[p[1] for p in pts],
                                     mode='markers+text', text=[p[2] for p in pts],
                                     textposition='top center',
                                     marker=dict(color=PURPLE_DK, size=8, symbol='diamond'),
                                     name='pivot', showlegend=False), row=1, col=1)
    for pts in polylines:
        if len(pts) >= 2:
            fig.add_trace(go.Scatter(x=dates[[p[0] for p in pts]], y=[p[1] for p in pts],
                                     mode='lines', line=dict(color=PURPLE_DK, width=1.6, dash='dash'),
                                     name='pivot line', showlegend=False), row=1, col=1)

    # cutoff marker: candle end < S; day-S data never plotted (arrays already truncated)
    fig.add_vline(x=dates[n - 1], line=dict(color=CUT, width=1.4, dash='dash'))
    fig.add_annotation(x=dates[n - 1], yref='paper', y=1.0, text='cutoff (setup-date open)',
                       showarrow=False, yshift=44, font=dict(size=10, color=CUT))

    title = f'{ticker} — {recipe_id}' if ticker else recipe_id
    fig.update_layout(
        title=dict(text=title, font=dict(size=14)),
        shapes=shapes,
        annotations=list(fig.layout.annotations or []),
        xaxis_rangeslider_visible=False,
        template='plotly_white',
        margin=dict(l=60, r=90, t=110, b=40),
        height=720,
    )
    # label box: measured quantity + answer + binary YES/NO readout
    txt = f'<b>{recipe_id}</b><br>{label}' + (f'<br><b>{answer}</b>' if answer else '')
    if binary is not None:
        lines = []
        for b in binary:
            a = b['a']
            colour = {'YES': '#15803d', 'NO': '#b91c1c'}.get(a, '#9ca3af')
            lines.append(f"<span style='color:{colour}'><b>{a}</b></span> "
                         f"<b>{b['qid']}</b>: {b['q']}")
        txt += ('<br>--- binary questions (§0b 22:51/23:05; feature + comparator '
                '+ literal threshold; NOT_EVALUABLE excluded, never silently NO) ---'
                + '<br>' + '<br>'.join(lines))
    fig.add_annotation(x=0.005, xref='paper', y=0.985, yref='paper', text=txt, showarrow=False,
                       align='left', bgcolor='rgba(250,250,252,0.94)', bordercolor=PURPLE_DK,
                       borderwidth=1, font=dict(size=10), xanchor='left', yanchor='top')
    return fig
