"""
艾艾精工形态模板提取 v2

自动检测启动日，构建两个模板：
- 模板A（蓄势段）: 启动日前 60 个交易日
- 模板B（拉升段）: 启动日后 20 个交易日
"""

import pandas as pd
import numpy as np
from src.data_source import get_kline


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


def build_templates(code: str = "603580", pre_days: int = 60, post_days: int = 20) -> dict:
    df = get_kline(code, days=300)
    if df is None or len(df) < 200:
        raise RuntimeError("无法获取模板K线数据")

    df = df.reset_index(drop=True)
    launch_idx = detect_launch_day(df)
    if launch_idx < 0:
        raise RuntimeError("未检测到启动日")

    pre_seg = df.iloc[launch_idx - pre_days:launch_idx].reset_index(drop=True)
    post_seg = df.iloc[launch_idx:launch_idx + post_days].reset_index(drop=True)

    launch_date = str(df.iloc[launch_idx]["date"].date())

    return {
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
