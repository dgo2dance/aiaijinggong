#!/usr/bin/env python3
"""
生成形态对比可视化 HTML 报告
- 艾艾精工模板走势（锚定启动日）
- Top N 命中个股的同期走势（归一化叠加）
"""

import pandas as pd
import numpy as np
from datetime import datetime
from src.data_source import get_kline
from src.template import build_templates, detect_launch_day


def build_report(csv_path: str, top_n: int = 12, out_html: str = None):
    df = pd.read_csv(csv_path)
    core = df[df["分类"].isin(["刚启动(拉升初期)", "启动前(蓄势中)"])]
    if len(core) < top_n:
        obs = df[df["分类"] == "形态接近(观察)"].head(top_n - len(core))
        core = pd.concat([core, obs])
    top = core.head(top_n)

    try:
        templates = build_templates()
    except Exception as e:
        print(f"构建模板失败: {e}")
        print("生成简化报告（无走势图）")
        return _build_simple_report(df, top, out_html)

    tmpl_pre = templates["pre"]["price_seq"]
    tmpl_post = templates["post"]["price_seq"]
    launch_date = templates["launch_date"]

    series = []
    tmpl_full = np.concatenate([tmpl_pre, tmpl_post]) * 100
    x_full = list(range(-len(tmpl_pre), len(tmpl_post)))
    series.append(("艾艾精工(模板)", tmpl_full, "#d62728", 3.0))

    for _, row in top.iterrows():
        code = str(row["代码"]).zfill(6)
        try:
            kdf = get_kline(code, days=120)
        except Exception:
            kdf = None
        if kdf is None or len(kdf) < 80:
            continue
        seg = kdf.tail(len(tmpl_pre) + len(tmpl_post))
        if len(seg) < 40:
            continue
        norm = seg["close"].values / seg["close"].values[0] * 100
        xs = list(range(len(x_full) - len(norm), len(x_full)))
        cat = row["分类"]
        series.append((f"{row['名称']}({row['代码']}) {row['拉升相似度']:.0f}分 [{cat[:4]}]",
                       norm, None, 1.5))

    W, H = 960, 480
    PAD_L, PAD_R, PAD_T, PAD_B = 50, 20, 30, 40
    all_vals = np.concatenate([s[1] for s in series])
    vmin, vmax = all_vals.min(), all_vals.max()
    n_x = len(x_full)

    def X(i):
        return PAD_L + (i + len(tmpl_pre)) / (n_x - 1) * (W - PAD_L - PAD_R)

    def Y(v):
        return H - PAD_B - (v - vmin) / (vmax - vmin + 1e-9) * (H - PAD_T - PAD_B)

    palette = ["#1f77b4", "#2ca02c", "#9467bd", "#8c564b", "#e377c2",
               "#7f7f7f", "#bcbd22", "#17becf", "#ff7f0e"]
    paths = []
    for idx, (name, vals, color, width) in enumerate(series):
        color = color or palette[(idx - 1) % len(palette)]
        pts = " ".join(f"{X(x_full[-len(vals)] + k):.1f},{Y(v):.1f}" for k, v in enumerate(vals))
        paths.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                     f'stroke-width="{width}" opacity="0.85"/>')

    lx = X(0)
    lines = [f'<line x1="{lx:.0f}" y1="{PAD_T}" x2="{lx:.0f}" y2="{H-PAD_B}" '
             f'stroke="#d62728" stroke-dasharray="4,4" opacity="0.6"/>',
             f'<text x="{lx+4:.0f}" y="{PAD_T+14}" fill="#d62728" font-size="12">启动日 {launch_date}</text>']

    y_ticks = np.linspace(vmin, vmax, 5)
    axis = []
    for v in y_ticks:
        axis.append(f'<text x="{PAD_L-8}" y="{Y(v)+4:.0f}" text-anchor="end" font-size="11" fill="#666">{v:.0f}</text>')
        axis.append(f'<line x1="{PAD_L}" y1="{Y(v):.0f}" x2="{W-PAD_R}" y2="{Y(v):.0f}" stroke="#eee"/>')

    legend = "".join(
        f'<circle cx="{PAD_L + i*230}" cy="{12}" r="4" fill="{s[2] or palette[(i-1)%len(palette)]}"/>'
        f'<text x="{PAD_L + i*230 + 8}" y="{16}" font-size="11" fill="#333">{s[0][:22]}</text>'
        for i, s in enumerate(series) if i < 8
    )
    legend2 = "".join(
        f'<circle cx="{PAD_L + (i-8)*230}" cy="{30}" r="4" fill="{s[2] or palette[(i-1)%len(palette)]}"/>'
        f'<text x="{PAD_L + (i-8)*230 + 8}" y="{34}" font-size="11" fill="#333">{s[0][:22]}</text>'
        for i, s in enumerate(series) if 8 <= i < 16
    )

    svg = (f'<svg viewBox="0 0 {W} {H}" style="width:100%;background:#fff">'
           + "".join(axis) + "".join(lines) + "".join(paths)
           + f'<g>{legend}{legend2}</g></svg>')

    table_rows = ""
    for _, r in top.iterrows():
        color = "#fff3e0" if "刚启动" in str(r["分类"]) else ("#e8f5e9" if "启动前" in str(r["分类"]) else "#fff")
        table_rows += (
            f'<tr style="background:{color}">'
            f'<td>{r["代码"]}</td><td>{r["名称"]}</td><td>{r["现价"]}</td>'
            f'<td>{r["流通市值(亿)"]}</td><td>{r["分类"]}</td>'
            f'<td><b>{r["拉升相似度"]}</b></td><td>{r["蓄势相似度"]}</td>'
            f'<td>{r["匹配段相关"]}</td><td>{r["匹配段DTW"]}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>艾艾精工形态相似扫描报告</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:24px;background:#fafafa;color:#333}}
h1{{font-size:22px}} h2{{font-size:16px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:13px}}
th,td{{border:1px solid #e0e0e0;padding:6px 10px;text-align:center}}
th{{background:#f5f5f5}}
.note{{background:#fff8e1;padding:10px 14px;border-left:4px solid #ffb300;font-size:13px;margin:14px 0}}
</style></head>
<body>
<h1>艾艾精工形态相似扫描报告</h1>
<p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} ｜ 模板锚点：603580 启动日 {launch_date}</p>
<div class="note">
说明：候选股走势<strong>右对齐</strong>叠加到模板坐标系（横轴=相对启动日的交易日偏移）。
红色粗线为艾艾精工模板（蓄势60天+拉升20天），其余为命中个股（归一化起点=100）。
形状相关性&gt;0.8 且 DTW&lt;2 为高度相似。
</div>
<h2>走势叠加对比</h2>
{svg}
<h2>命中明细（Top {len(top)}）</h2>
<table>
<tr><th>代码</th><th>名称</th><th>现价</th><th>流通市值(亿)</th><th>分类</th>
<th>拉升相似度</th><th>蓄势相似度</th><th>形状相关</th><th>DTW距离</th></tr>
{table_rows}
</table>
<h2>分类口径</h2>
<ul>
<li><b>刚启动(拉升初期)</b>：近20日节奏与艾艾精工连续涨停段高度相似，且近5日无深回撤</li>
<li><b>启动前(蓄势中)</b>：近60日节奏与艾艾精工横盘蓄势段高度相似</li>
<li><b>形态接近(观察)</b>：综合相似但未达硬门槛，供观察</li>
</ul>
<p class="note">数据源：新浪行情（不复权）。本报告仅为形态量化筛选结果，不构成投资建议。</p>
</body></html>"""

    out_html = out_html or f"aiai_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"报告已生成: {out_html}")
    return out_html


def _build_simple_report(df, top, out_html):
    table_rows = ""
    for _, r in top.iterrows():
        color = "#fff3e0" if "刚启动" in str(r["分类"]) else ("#e8f5e9" if "启动前" in str(r["分类"]) else "#fff")
        table_rows += (
            f'<tr style="background:{color}">'
            f'<td>{r["代码"]}</td><td>{r["名称"]}</td><td>{r["现价"]}</td>'
            f'<td>{r["流通市值(亿)"]}</td><td>{r["分类"]}</td>'
            f'<td><b>{r["拉升相似度"]}</b></td><td>{r["蓄势相似度"]}</td>'
            f'<td>{r["匹配段相关"]}</td><td>{r["匹配段DTW"]}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>艾艾精工形态相似扫描报告</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:24px;background:#fafafa;color:#333}}
h1{{font-size:22px}} h2{{font-size:16px;margin-top:28px}}
table{{border-collapse:collapse;width:100%;background:#fff;font-size:13px}}
th,td{{border:1px solid #e0e0e0;padding:6px 10px;text-align:center}}
th{{background:#f5f5f5}}
.note{{background:#fff8e1;padding:10px 14px;border-left:4px solid #ffb300;font-size:13px;margin:14px 0}}
</style></head>
<body>
<h1>艾艾精工形态相似扫描报告</h1>
<p>生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div class="note">模板数据获取失败，仅显示数据表格。</div>
<h2>命中明细（Top {len(top)}）</h2>
<table>
<tr><th>代码</th><th>名称</th><th>现价</th><th>流通市值(亿)</th><th>分类</th>
<th>拉升相似度</th><th>蓄势相似度</th><th>形状相关</th><th>DTW距离</th></tr>
{table_rows}
</table>
<p class="note">数据源：新浪行情（不复权）。本报告仅为形态量化筛选结果，不构成投资建议。</p>
</body></html>"""

    out_html = out_html or f"aiai_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"简化报告已生成: {out_html}")
    return out_html


if __name__ == "__main__":
    import sys, glob
    csv_path = sys.argv[1] if len(sys.argv) > 1 else sorted(glob.glob("outputs/aiai_pattern_scan_*.csv"))[-1]
    build_report(csv_path)
