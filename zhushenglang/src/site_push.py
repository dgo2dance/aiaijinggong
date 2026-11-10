#!/usr/bin/env python3
"""推送每日扫描结果到生产站（jimu-flash-etf / https://etf.vosi.cc）

推送令牌写死在代码里（与服务端 backend/app/config.py 的 ZSL_PUSH_TOKEN 同值），免配置。
"""

import os
from datetime import datetime

import requests

DEFAULT_URL = "https://etf.vosi.cc/api/zsl/push"
TOKEN = "zsl_e7ab3ef2b0bb58f080b14d2e327712f5"


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return round(float(f), 4)


def build_items(results) -> list[dict]:
    """CSV/DataFrame 行 → 推送明细（snake_case，与服务端字段白名单一致）"""
    if results is None or getattr(results, "empty", True):
        return []
    items = []
    for _, r in results.head(200).iterrows():
        code = str(r.get("代码", "") or "").strip().zfill(6)
        if not code or code == "000000":
            continue
        items.append({
            "code": code,
            "name": str(r.get("名称", "") or ""),
            "price": _num(r.get("现价")),
            "float_mktcap_yi": _num(r.get("流通市值(亿)")),
            "category": str(r.get("分类", "") or ""),
            "pre_score": _num(r.get("蓄势相似度")),
            "post_score": _num(r.get("拉升相似度")),
            "pre_return": _num(r.get("蓄势段涨幅")),
            "post_return": _num(r.get("拉升段涨幅")),
            "dtw": _num(r.get("匹配段DTW")),
            "corr": _num(r.get("匹配段相关")),
            "vol_score": _num(r.get("量能形态")),
        })
    return items


def push_scan_to_site(results, templates=None, url: str = None) -> bool:
    url = url or os.environ.get("ZSL_PUSH_URL", DEFAULT_URL)

    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "launch_date": str((templates or {}).get("launch_date") or ""),
        "source": "zhushenglang",
        "items": build_items(results),
    }
    print(f"[SitePush] 推送到 {url} · {payload['date']} · {len(payload['items'])} 只")
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=20,
        )
        print(f"[SitePush] 响应 {resp.status_code}: {resp.text[:300]}")
        if resp.status_code == 200:
            print("[SitePush] 生产站推送成功")
            return True
        print("[SitePush] 生产站推送失败")
        return False
    except Exception as e:  # noqa: BLE001
        print(f"[SitePush] 生产站推送异常: {e}")
        return False
