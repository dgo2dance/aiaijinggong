"""
艾艾精工形态模板提取 v2

自动检测启动日，构建两个模板：
- 模板A（蓄势段）: 启动日前 60 个交易日
- 模板B（拉升段）: 启动日后 20 个交易日

支持缓存：首次构建后保存到本地，后续直接读取
"""

import os
import json
import pandas as pd
import numpy as np
from src.data_source import get_kline

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")
TEMPLATE_CACHE = os.path.join(CACHE_DIR, "template_cache.json")


def detect_launch_day(df: pd.DataFrame) -> int:
    df = df.copy()
    df["vol20"] = df["volume"].rolling(20).mean()
    for i in range(60, len(df)):
        row = df.iloc[i]
        pre30 = df.iloc[max(0, i - 30):i]
        pre30_ret = pre30["close"].iloc[-1] / pre30["close"].iloc[0] - 1 if len(pre30) > 5 else 0
        if (row["pct_chg"] > 8
                and row["vol20"] > 0
                and row["volume"] > 2 * row["vol20"]
                and pre30_ret < 0.15):
            return i
    return -1


def _norm_seq(arr: np.ndarray) -> np.ndarray:
    return arr / arr[0] if arr[0] != 0 else arr


def _save_cache(templates: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_data = {
        "pre": {
            "price_seq": templates["pre"]["price_seq"].tolist(),
            "vol_seq": templates["pre"]["vol_seq"].tolist(),
            "meta": templates["pre"]["meta"],
        },
        "post": {
            "price_seq": templates["post"]["price_seq"].tolist(),
            "vol_seq": templates["post"]["vol_seq"].tolist(),
            "meta": templates["post"]["meta"],
        },
        "launch_date": templates["launch_date"],
        "code": templates["code"],
    }
    with open(TEMPLATE_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
    print(f"模板已缓存到 {TEMPLATE_CACHE}")


def _load_cache() -> dict:
    if not os.path.exists(TEMPLATE_CACHE):
        return None
    try:
        with open(TEMPLATE_CACHE, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        return {
            "pre": {
                "price_seq": np.array(cache_data["pre"]["price_seq"]),
                "vol_seq": np.array(cache_data["pre"]["vol_seq"]),
                "meta": cache_data["pre"]["meta"],
            },
            "post": {
                "price_seq": np.array(cache_data["post"]["price_seq"]),
                "vol_seq": np.array(cache_data["post"]["vol_seq"]),
                "meta": cache_data["post"]["meta"],
            },
            "launch_date": cache_data["launch_date"],
            "code": cache_data["code"],
        }
    except Exception as e:
        print(f"读取缓存失败: {e}")
        return None


def build_templates(code: str = "603580", pre_days: int = 60, post_days: int = 20,
                    use_cache: bool = True) -> dict:
    if use_cache:
        cached = _load_cache()
        if cached:
            print("使用缓存模板")
            return cached

    df = get_kline(code, days=300)
    if df is None or len(df) < 200:
        cached = _load_cache()
        if cached:
            print("API获取失败，使用缓存模板")
            return cached
        raise RuntimeError("无法获取模板K线数据且无缓存")

    df = df.reset_index(drop=True)
    launch_idx = detect_launch_day(df)
    if launch_idx < 0:
        cached = _load_cache()
        if cached:
            print("未检测到启动日，使用缓存模板")
            return cached
        raise RuntimeError("未检测到启动日且无缓存")

    pre_seg = df.iloc[launch_idx - pre_days:launch_idx].reset_index(drop=True)
    post_seg = df.iloc[launch_idx:launch_idx + post_days].reset_index(drop=True)

    launch_date = str(df.iloc[launch_idx]["date"].date())

    templates = {
        "pre": {
            "price_seq": _norm_seq(pre_seg["close"].values.astype(float)),
            "vol_seq": (pre_seg["volume"].values / pre_seg["volume"].mean()),
            "pct_seq": pre_seg["pct_chg"].fillna(0).values,
            "meta": {
                "type": "蓄势段(启动前)",
                "days": len(pre_seg),
                "start": str(pre_seg["date"].iloc[0].date()),
                "end": str(pre_seg["date"].iloc[-1].date()),
                "total_return": float(pre_seg["close"].iloc[-1] / pre_seg["close"].iloc[0] - 1),
            },
        },
        "post": {
            "price_seq": _norm_seq(post_seg["close"].values.astype(float)),
            "vol_seq": (post_seg["volume"].values / post_seg["volume"].mean()),
            "pct_seq": post_seg["pct_chg"].fillna(0).values,
            "meta": {
                "type": "拉升段(启动后)",
                "days": len(post_seg),
                "start": launch_date,
                "end": str(post_seg["date"].iloc[-1].date()),
                "total_return": float(post_seg["close"].iloc[-1] / post_seg["close"].iloc[0] - 1),
            },
        },
        "launch_date": launch_date,
        "code": code,
    }

    if use_cache:
        _save_cache(templates)

    return templates
