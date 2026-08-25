"""
形态匹配引擎 v2（双模板版）

匹配逻辑：
- pre_score  (蓄势相似度): 候选股最近N天 vs 模板A
- post_score (拉升相似度): 候选股最近M天 vs 模板B

评分 = DTW距离(35%) + 形状相关(35%) + 量能形态(15%) + 涨幅接近度(15%)
"""

import numpy as np
import pandas as pd
from typing import Optional


def zscore(x: np.ndarray) -> np.ndarray:
    s = np.std(x)
    if s == 0:
        return np.zeros_like(x)
    return (x - np.mean(x)) / s


def dtw_distance(a: np.ndarray, b: np.ndarray, window_frac: int = 8) -> float:
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return np.inf
    w = max(abs(n - m), max(n, m) // window_frac, 1)
    dtw = np.full((n + 1, m + 1), np.inf)
    dtw[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(max(1, i - w), min(m, i + w) + 1):
            cost = (a[i - 1] - b[j - 1]) ** 2
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])
    return float(np.sqrt(dtw[n, m]))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    za, zb = zscore(a), zscore(b)
    L = min(len(za), len(zb))
    za, zb = za[:L], zb[:L]
    denom = np.linalg.norm(za) * np.linalg.norm(zb)
    if denom == 0:
        return 0.0
    return float(np.dot(za, zb) / denom)


def vol_pattern(vol_norm: np.ndarray, pre_frac: float = 0.6) -> float:
    n = len(vol_norm)
    k = int(n * pre_frac)
    if k == 0 or n - k == 0:
        return 0.0
    pre_mean = vol_norm[:k].mean()
    post_mean = vol_norm[k:].mean()
    if pre_mean == 0:
        return 0.0
    ratio = post_mean / pre_mean
    if 1.3 <= ratio <= 4:
        return 1.0
    if 1.1 <= ratio < 1.3:
        return 0.7
    if 4 < ratio <= 6:
        return 0.6
    if 0.9 <= ratio < 1.1:
        return 0.4
    return 0.0


def match_segment(seg: pd.DataFrame, tmpl: dict) -> Optional[dict]:
    n_need = tmpl["meta"]["days"]
    if len(seg) < n_need:
        return None
    seg = seg.tail(n_need)

    c_close = seg["close"].values.astype(float)
    c_close_norm = c_close / c_close[0] if c_close[0] != 0 else c_close
    t_close = tmpl["price_seq"]

    c_vol = seg["volume"].values.astype(float)
    c_vol_norm = c_vol / c_vol.mean() if c_vol.mean() > 0 else c_vol

    d = dtw_distance(zscore(t_close), zscore(c_close_norm))
    dtw_score = max(0.0, 1 - d / 3.0)

    c = corr(t_close, c_close_norm)
    corr_score = max(0.0, c)

    vs = vol_pattern(c_vol_norm)

    c_ret = c_close[-1] / c_close[0] - 1
    t_ret = tmpl["meta"]["total_return"]
    ret_diff = abs(np.log1p(max(c_ret, -0.9)) - np.log1p(t_ret))
    ret_score = max(0.0, 1 - ret_diff / 2.5)

    shape = dtw_score * 0.5 + corr_score * 0.5

    total = shape * 0.80 + vs * 0.10 + ret_score * 0.10
    return {
        "dtw": round(d, 4),
        "dtw_score": round(dtw_score, 4),
        "corr": round(c, 4),
        "shape": round(shape, 4),
        "vol_score": round(vs, 4),
        "cand_return": round(float(c_ret), 4),
        "tmpl_return": round(float(t_ret), 4),
        "ret_score": round(ret_score, 4),
        "score": round(total * 100, 2),
    }


def match_stock(df: pd.DataFrame, templates: dict) -> Optional[dict]:
    pre_n = templates["pre"]["meta"]["days"]
    post_n = templates["post"]["meta"]["days"]
    if len(df) < max(pre_n, post_n):
        return None

    pre_m = match_segment(df, templates["pre"])
    post_m = match_segment(df, templates["post"])
    if pre_m is None and post_m is None:
        return None

    pre_score = pre_m["score"] if pre_m else 0
    post_score = post_m["score"] if post_m else 0
    pre_shape = pre_m["shape"] if pre_m else 0
    post_shape = post_m["shape"] if post_m else 0

    recent_drawdown_ok = True
    if len(df) >= 5:
        recent5 = df.tail(5)
        dd = 1 - recent5["close"].iloc[-1] / recent5["close"].max()
        if dd > 0.12:
            recent_drawdown_ok = False

    cat = ""
    if (post_score >= 55 and post_shape >= 0.35
            and post_score >= pre_score and recent_drawdown_ok):
        cat = "刚启动(拉升初期)"
    elif pre_score >= 55 and pre_shape >= 0.35:
        cat = "启动前(蓄势中)"
    elif max(pre_score, post_score) >= 48:
        cat = "形态接近(观察)"

    return {
        "pre_score": pre_score,
        "post_score": post_score,
        "category": cat,
        "pre_detail": pre_m,
        "post_detail": post_m,
    }
