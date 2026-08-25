#!/usr/bin/env python3
"""更新 docs/index.html 报告列表"""
import os
import glob

def update_index():
    reports = sorted(glob.glob("docs/aiai_report_*.html"), reverse=True)
    if not reports:
        print("No reports found")
        return

    links = ""
    for r in reports[:30]:
        name = os.path.basename(r)
        date_part = name.replace("aiai_report_", "").replace(".html", "")
        links += f'    <li><a href="{name}">{date_part}</a></li>\n'

    html = f'''<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>艾艾精工形态扫描报告</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;margin:24px;background:#fafafa;color:#333}}
h1{{font-size:22px}} a{{color:#1a73e8}} ul{{font-size:15px;line-height:2}}
</style></head>
<body>
<h1>艾艾精工形态相似扫描报告</h1>
<p>每日收盘后自动扫描全A股，找出与艾艾精工走势形态相似的标的。</p>
<h2>最新报告</h2>
<ul>
{links}</ul>
<p style="color:#999;font-size:12px">自动生成，仅供参考，不构成投资建议。</p>
</body></html>'''

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Updated index.html with {len(reports)} reports")

if __name__ == "__main__":
    update_index()
