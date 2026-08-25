#!/usr/bin/env python3
"""更新 docs/index.html 报告列表"""
import os
import glob

def update_index():
    print(f"当前工作目录: {os.getcwd()}")
    print(f"docs目录是否存在: {os.path.exists('docs')}")

    if os.path.exists('docs'):
        print(f"docs目录内容: {os.listdir('docs')}")

    reports = sorted(glob.glob("docs/aiai_report_*.html"), reverse=True)
    print(f"找到报告文件: {len(reports)} 个")

    if not reports:
        print("No reports found in docs/")
        return

    links = ""
    for r in reports[:30]:
        name = os.path.basename(r)
        date_part = name.replace("aiai_report_", "").replace(".html", "")
        # 格式化日期显示：20260825 -> 2026-08-25
        if len(date_part) == 8 and date_part.isdigit():
            date_display = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        else:
            date_display = date_part
        links += f'    <li><a href="{name}">{date_display}</a></li>\n'

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
