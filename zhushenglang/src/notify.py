"""
微信 PushPlus 推送模块
"""

import os
import requests


def send_pushplus(token: str, title: str, content: str) -> bool:
    print(f"[PushPlus] 开始推送...")
    print(f"[PushPlus] Token长度: {len(token) if token else 0}")
    print(f"[PushPlus] 标题: {title}")

    if not token:
        print("[PushPlus] 未配置 PUSHPLUS_TOKEN，跳过微信推送")
        return False

    url = "http://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown"
    }

    try:
        print(f"[PushPlus] 发送请求到 {url}")
        resp = requests.post(url, json=payload, timeout=15)
        print(f"[PushPlus] 响应状态码: {resp.status_code}")
        print(f"[PushPlus] 响应内容: {resp.text[:500]}")

        if resp.status_code == 200:
            result = resp.json()
            if result.get("code") == 200:
                print("[PushPlus] 微信推送成功！")
                return True
            else:
                print(f"[PushPlus] 推送失败: {result.get('msg', 'unknown')}")
                return False
        else:
            print(f"[PushPlus] HTTP请求失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"[PushPlus] 微信推送异常: {e}")
        return False


def build_scan_report_message(results, templates) -> str:
    from datetime import datetime

    launch_date = templates.get("launch_date", "N/A")
    lines = [
        f"## 艾艾精工形态扫描报告",
        f"**扫描时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**模板锚点**: 603580 启动日 {launch_date}",
        "",
        "---",
        "",
    ]

    if results is None or results.empty:
        lines.append("**本次扫描未发现符合条件的标的**")
        lines.append("")
        lines.append("可能原因：")
        lines.append("- API数据源受限（GitHub Actions环境）")
        lines.append("- 市场暂无高相似度标的")
        lines.append("---")
        lines.append("*数据源: 新浪行情 | 仅供参考，不构成投资建议*")
        return "\n".join(lines)

    top = results.head(10)

    lines.append(f"### Top {len(top)} 命中标的")
    lines.append("")

    for idx, (_, r) in enumerate(top.iterrows(), 1):
        cat = str(r.get("分类", ""))
        if "刚启动" in cat:
            icon = " "
        elif "启动前" in cat:
            icon = " "
        else:
            icon = " "

        pre_score = r.get("蓄势相似度", 0)
        post_score = r.get("拉升相似度", 0)
        max_score = max(pre_score, post_score)

        lines.append(f"**{idx}. {r.get('名称', '')} ({r.get('代码', '')})** {icon}")
        lines.append(f"- 现价: {r.get('现价', 'N/A')} | 流通市值: {r.get('流通市值(亿)', 'N/A')}亿")
        lines.append(f"- **综合分: {max_score:.0f}** | 蓄势: {pre_score:.0f} | 拉升: {post_score:.0f}")
        lines.append(f"- 分类: {cat}")
        lines.append("")

    lines.append("---")
    lines.append("*数据源: 新浪行情 | 仅供参考，不构成投资建议*")

    return "\n".join(lines)


def push_scan_results(results, templates, token=None):
    print("[PushPlus] 准备推送扫描结果...")

    if token is None:
        token = os.environ.get("PUSHPLUS_TOKEN", "")
        print(f"[PushPlus] 从环境变量读取Token: {'已设置' if token else '未设置'}")
    else:
        print(f"[PushPlus] 使用传入Token: {'已设置' if token else '未设置'}")

    message = build_scan_report_message(results, templates)
    print(f"[PushPlus] 消息长度: {len(message)} 字符")

    from datetime import datetime
    title = f" 形态扫描 {datetime.now().strftime('%m-%d %H:%M')}"

    return send_pushplus(token, title, message)
