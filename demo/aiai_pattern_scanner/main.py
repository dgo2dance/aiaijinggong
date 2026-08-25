#!/usr/bin/env python3
"""
艾艾精工形态相似选股器 - 单票诊断入口

用法:
  python3 main.py --code 600713
  python3 main.py --code 600713 --pre-days 60 --post-days 20
"""

import argparse
import json

from data_source import get_kline
from template import build_templates
from matcher import match_stock


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", required=True, help="股票代码，如 600713")
    ap.add_argument("--pre-days", type=int, default=60, help="蓄势模板长度(交易日)")
    ap.add_argument("--post-days", type=int, default=20, help="拉升模板长度(交易日)")
    args = ap.parse_args()

    templates = build_templates(pre_days=args.pre_days, post_days=args.post_days)
    print(f"\n艾艾精工启动日: {templates['launch_date']}\n"
          f"模板A 蓄势段 [{templates['pre']['meta']['start']} ~ {templates['pre']['meta']['end']}] "
          f"区间涨幅 {templates['pre']['meta']['total_return']:.1%}\n"
          f"模板B 拉升段 [{templates['post']['meta']['start']} ~ {templates['post']['meta']['end']}] "
          f"区间涨幅 {templates['post']['meta']['total_return']:.1%}\n")

    code = str(args.code).zfill(6)
    df = get_kline(code, days=120)
    if df is None:
        print("获取数据失败")
        return

    m = match_stock(df, templates)
    print(f"===== 与 {code} 的双模板对比 =====")
    if m is None:
        print("数据不足，无法对比")
        return
    print(json.dumps({
        "pre_score": m["pre_score"],
        "post_score": m["post_score"],
        "category": m["category"],
        "pre_detail": m["pre_detail"],
        "post_detail": m["post_detail"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()