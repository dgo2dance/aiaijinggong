"""
数据获取模块 v2（新浪行情接口）+ 本地股票池辅助

数据策略：
- K 线：新浪公开接口（沙箱环境可访问）
- 股票池：通过本地内置文件 / 用户传入 CSV / akshare(tushare) 离线库三种来源
"""

import requests
import pandas as pd
from typing import Optional
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://finance.sina.com.cn/",
}

SEED_CENTRAL_POOL = [
    ("600089", "特变电工", "河南"), ("601777", "力帆科技", "河南"), ("002460", "赣锋锂业", "江西"),
    ("002466", "天齐锂业", "四川"), ("600703", "三安光电", "湖北"), ("000783", "长江证券", "湖北"),
    ("600005", "武钢股份", "湖北"), ("000932", "华菱钢铁", "湖南"), ("002251", "步步高", "湖南"),
    ("000157", "中联重科", "湖南"), ("600690", "海信家电", "山东"), ("000869", "张裕A", "山东"),
    ("600338", "西藏珠峰", "西藏"), ("600547", "山东黄金", "山东"),
    ("601666", "平煤股份", "河南"), ("601699", "潞安环能", "山西"),
    ("603580", "艾艾精工", "上海"),
]


def _to_sina_symbol(code: str) -> str:
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def _tencent_symbol(code: str) -> str:
    if code.startswith(("6", "9", "5")):
        return f"sh{code}"
    if code.startswith(("4", "8")):
        return f"bj{code}"
    return f"sz{code}"


def get_kline_tencent(code: str, days: int = 320) -> Optional[pd.DataFrame]:
    sym = _tencent_symbol(code)
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sym},day,,,{days},qfq"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        d = r.json().get("data", {}).get(sym, {})
        rows = d.get("qfqday") or d.get("day") or []
        if not rows:
            return None
        df = pd.DataFrame(
            [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows],
            columns=["date", "open", "close", "high", "low", "volume"],
        )
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        df["pct_chg"] = df["close"].pct_change() * 100
        df["amount"] = df["close"] * df["volume"] * 100
        return df[["date", "open", "high", "low", "close", "volume", "pct_chg", "amount"]]
    except Exception as e:
        print(f"[ERR-TX] {code} 获取失败: {e}")
        return None


def get_kline(code: str, days: int = 300) -> Optional[pd.DataFrame]:
    symbol = _to_sina_symbol(code)
    url = (
        f"https://quotes.sina.cn/cn/api/openapi.php/"
        f"CN_MarketDataService.getKLineData"
        f"?symbol={symbol}&scale=240&ma=no&datalen={days}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200 and r.text.startswith("{"):
            data = r.json()
            rows = data.get("result", {}).get("data", [])
            if rows:
                df = pd.DataFrame(rows)
                df = df.rename(columns={
                    "day": "date", "open": "open", "high": "high",
                    "low": "low", "close": "close", "volume": "volume",
                })
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["date"] = pd.to_datetime(df["date"])
                df = df.sort_values("date").reset_index(drop=True)
                df["pct_chg"] = df["close"].pct_change() * 100
                df["amount"] = df["close"] * df["volume"] * 100
                return df[["date", "open", "high", "low", "close", "volume", "pct_chg", "amount"]]
    except Exception:
        pass
    return get_kline_tencent(code, days=days)


def get_stock_list_sina(pages: int = 60, per_page: int = 100) -> pd.DataFrame:
    all_rows = []
    for page in range(1, pages + 1):
        try:
            r = requests.get(
                "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData",
                params={"page": page, "num": per_page, "sort": "symbol", "asc": 1,
                        "node": "hs_a", "symbol": "", "_s_r_a": "page"},
                headers=HEADERS, timeout=10)
            rows = r.json()
            if not rows:
                break
            all_rows.extend(rows)
        except Exception:
            continue
    if not all_rows:
        return pd.DataFrame(columns=["code", "name"])
    df = pd.DataFrame(all_rows)
    df = df[["code", "name", "trade", "changepercent", "nmc", "turnoverratio"]]
    df.columns = ["code", "name", "price", "pct_chg", "float_mktcap_wan", "turnover"]
    df["code"] = df["code"].astype(str).str.zfill(6)
    return df


def load_stock_pool(source: str = "sina") -> pd.DataFrame:
    if source == "sina":
        df = get_stock_list_sina()
        if df.empty:
            print("[WARN] 在线获取失败，回退到 seed")
            return load_stock_pool("seed")
        return df
    if source == "seed":
        return pd.DataFrame(SEED_CENTRAL_POOL, columns=["code", "name", "province"])
    if source == "csv":
        candidates = [
            getattr(load_stock_pool, "_file", None),
            "examples/stock_pool_demo.csv",
            "stock_pool.csv",
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return pd.read_csv(path)
        print("[WARN] 找不到任何 stock_pool CSV，回退到 seed")
        return load_stock_pool("seed")
    if source == "tushare":
        try:
            import tushare as ts
            pro = ts.pro_api()
            df = pro.stock_basic(list_status="L",
                                 fields="ts_code,name,area,industry,list_date")
            return df
        except Exception as e:
            print(f"[ERR] tushare 加载失败: {e}")
            return load_stock_pool("seed")
    return pd.DataFrame(columns=["code", "name"])


def is_central(area: str) -> bool:
    central = ["河南", "湖北", "湖南", "安徽", "江西", "山西"]
    return any(c in str(area) for c in central)
