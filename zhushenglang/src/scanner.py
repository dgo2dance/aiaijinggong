#!/usr/bin/env python3
"""
全市场形态相似扫描器（并发版）

用法:
  python3 -m src.scanner                           # 全 A 扫描（默认）
  python3 -m src.scanner --pool csv --limit 7      # 演示池
  python3 -m src.scanner --limit 300 --workers 12  # 快速测试
"""

import argparse
import os
import time
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.data_source import get_kline, load_stock_pool
from src.template import build_templates
from src.matcher import match_stock
from src.notify import push_scan_results


def scan(pool: pd.DataFrame, templates: dict, limit: int = 0,
         min_mktcap: float = 0, max_mktcap: float = 0,
         exclude_bj: bool = True,
         workers: int = 16, min_score: float = 50.0,
         out_path: str = None) -> pd.DataFrame:
    df = pool.copy()
    df["code"] = df["code"].astype(str).str.zfill(6)
    if exclude_bj:
        df = df[~df["code"].str.startswith(("4", "8", "92", "688"))]
    has_mkt = "float_mktcap_wan" in df.columns
    if min_mktcap > 0 and has_mkt:
        df = df[df["float_mktcap_wan"] >= min_mktcap * 10000]
    if max_mktcap > 0 and has_mkt:
        df = df[df["float_mktcap_wan"] <= max_mktcap * 10000]
    if limit > 0:
        df = df.head(limit)

    codes = df["code"].tolist()
    print(f"预过滤后待扫描: {len(codes)} 只，线程数={workers}\n")

    results = []
    done = 0
    t0 = time.time()

    def work(code: str):
        code_z = code.zfill(6)
        kdf = get_kline(code_z, days=120)
        if kdf is None or len(kdf) < 60:
            return None
        m = match_stock(kdf, templates)
        if m is None:
            return None
        m["code"] = code_z
        return m

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(work, c): c for c in codes}
        for fut in as_completed(futures):
            done += 1
            if done % 200 == 0:
                speed = done / (time.time() - t0)
                print(f"进度 {done}/{len(codes)} ({speed:.0f} 只/秒) 已命中 {len(results)}")
            try:
                r = fut.result()
            except Exception:
                continue
            if r and max(r["pre_score"], r["post_score"]) >= min_score:
                info = df[df["code"] == r["code"]].iloc[0]
                r["name"] = info.get("name", "")
                r["price"] = info.get("price") if "price" in df.columns else None
                r["float_mktcap_yi"] = (round(info.get("float_mktcap_wan", 0) / 10000, 1)
                                         if "float_mktcap_wan" in df.columns else None)
                results.append(r)

    out = pd.DataFrame([{
        "代码": r["code"],
        "名称": r["name"],
        "现价": r["price"],
        "流通市值(亿)": r["float_mktcap_yi"],
        "分类": r["category"],
        "蓄势相似度": r["pre_score"],
        "拉升相似度": r["post_score"],
        "蓄势段涨幅": r["pre_detail"]["cand_return"] if r["pre_detail"] else None,
        "拉升段涨幅": r["post_detail"]["cand_return"] if r["post_detail"] else None,
        "匹配段DTW": (r["post_detail"]["dtw"] if (r["post_detail"] and r["post_score"] >= r["pre_score"])
                   else (r["pre_detail"]["dtw"] if r["pre_detail"] else None)),
        "匹配段相关": (r["post_detail"]["corr"] if (r["post_detail"] and r["post_score"] >= r["pre_score"])
                   else (r["pre_detail"]["corr"] if r["pre_detail"] else None)),
        "量能形态": (r["post_detail"]["vol_score"] if (r["post_detail"] and r["post_score"] >= r["pre_score"])
                 else (r["pre_detail"]["vol_score"] if r["pre_detail"] else None)),
    } for r in results])

    if not out.empty:
        out["_max"] = out[["蓄势相似度", "拉升相似度"]].max(axis=1)
        out = out.sort_values("_max", ascending=False).drop(columns="_max")

    if out_path:
        fname = out_path
    else:
        fname = f"outputs/aiai_pattern_scan_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    os.makedirs(os.path.dirname(fname) or ".", exist_ok=True)
    out.to_csv(fname, index=False, encoding="utf-8-sig")
    print(f"\n扫描完成: {len(out)} 只命中，耗时 {time.time()-t0:.0f}s，结果: {fname}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", default="sina", choices=["sina", "csv", "seed"],
                    help="股票池来源")
    ap.add_argument("--limit", type=int, default=0, help="扫描数量(0=全部)")
    ap.add_argument("--min-mktcap", type=float, default=10, help="最小流通市值(亿)")
    ap.add_argument("--max-mktcap", type=float, default=0, help="最大流通市值(亿)")
    ap.add_argument("--exclude-bj", action="store_true", default=True, help="排除北交所")
    ap.add_argument("--workers", type=int, default=16, help="并发线程数")
    ap.add_argument("--min-score", type=float, default=50.0, help="最低相似分")
    ap.add_argument("--pre-days", type=int, default=60, help="蓄势模板长度")
    ap.add_argument("--post-days", type=int, default=20, help="拉升模板长度")
    ap.add_argument("--out", default=None, help="输出 CSV 路径")
    ap.add_argument("--pool-file", default=None, help="自定义 CSV 路径")
    ap.add_argument("--push", action="store_true", default=False, help="推送Top结果到微信")
    args = ap.parse_args()

    print("构建艾艾精工双模板 ...")
    templates = build_templates(pre_days=args.pre_days, post_days=args.post_days)
    print(f"启动日: {templates['launch_date']}")
    print(f"模板A(蓄势): {templates['pre']['meta']['start']}~{templates['pre']['meta']['end']} "
          f"涨幅{templates['pre']['meta']['total_return']:.1%}")
    print(f"模板B(拉升): {templates['post']['meta']['start']}~{templates['post']['meta']['end']} "
          f"涨幅{templates['post']['meta']['total_return']:.1%}\n")

    print(f"加载股票池 (来源={args.pool}) ...")
    if args.pool == "csv" and args.pool_file:
        from src.data_source import load_stock_pool as _lsp
        _lsp._file = args.pool_file
    pool = load_stock_pool(args.pool)
    if pool.empty:
        print("股票池为空")
        return
    print(f"共 {len(pool)} 只\n")

    out = scan(pool, templates, limit=args.limit, min_mktcap=args.min_mktcap,
               max_mktcap=args.max_mktcap,
               exclude_bj=args.exclude_bj, workers=args.workers,
               min_score=args.min_score, out_path=args.out)

    if not out.empty:
        print("\n===== 相似形态 Top 20 =====")
        print(out.head(20).to_string(index=False))
    else:
        print("\n本次扫描未发现符合条件的标的")

    if args.push:
        print("\n推送微信通知...")
        push_scan_results(out, templates)


if __name__ == "__main__":
    main()
