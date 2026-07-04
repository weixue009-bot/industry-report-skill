#!/usr/bin/env python3
"""公司深度分析 JSON 模板生成器（v1.0）。

从采集的 raw 数据（profile.json + financial.json + valuation.json + reports.json）
自动填充 analysis.json 的结构化数据字段（identity/financial_snapshot/sources 等），
输出一个半成品 JSON 框架。AI Agent 只需补全文本分析字段（one_sentence_view、
chain_positioning、growth_drivers、profit_logic 等 15 个文本字段）。

用法：
  PYTHONIOENCODING=utf-8 python company_analysis.py --code 002202 --work-dir "."

输出：
  analysis/company/{代码}/analysis.json
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path


def load_json(path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fmt_cap_str(mcap_yi):
    """格式化市值字符串。"""
    if mcap_yi is None:
        return "N/A"
    try:
        val = float(mcap_yi)
        return f"{val:.2f}亿"
    except (ValueError, TypeError):
        return str(mcap_yi)


def build_identity(profile, valuation):
    """从 profile + valuation 构建 company_identity。"""
    mcap_yi = profile.get("market_cap_yi") or valuation.get("market_cap_yi")
    if mcap_yi is None and profile.get("market_cap"):
        mcap_yi = profile["market_cap"] / 1e8

    return {
        "code": profile.get("code", ""),
        "name": profile.get("name", ""),
        "industry": profile.get("industry", ""),
        "market_cap": fmt_cap_str(mcap_yi),
        "price": profile.get("price") or valuation.get("price"),
        "pe_ttm": profile.get("pe_ttm") or valuation.get("pe_ttm"),
        "pb": profile.get("pb") or valuation.get("pb"),
        "change_pct": profile.get("change_pct") or valuation.get("change_pct"),
        "listing_date": profile.get("listing_date", ""),
        "main_business": profile.get("main_business", ""),
    }


def build_financial_snapshot(financial):
    """从 financial.json 构建 financial_snapshot。"""
    if not financial:
        return {}
    return {
        "report_date": financial.get("report_date", ""),
        "revenue": financial.get("revenue"),
        "revenue_unit": "亿",
        "revenue_yoy": financial.get("revenue_yoy"),
        "parent_netprofit": financial.get("parent_netprofit"),
        "profit_unit": "亿",
        "profit_yoy": financial.get("profit_yoy"),
        "gross_margin": financial.get("gross_margin"),
        "net_margin": financial.get("net_margin"),
        "roe": financial.get("roe"),
        "debt_ratio": financial.get("debt_ratio"),
        "basic_eps": financial.get("basic_eps"),
    }


def main():
    parser = argparse.ArgumentParser(
        description="公司深度分析 JSON 模板生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  company_analysis.py --code 002202 --work-dir "."
    → 从 raw/company/002202/ 读取 raw 数据
    → 输出 analysis/company/002202/analysis.json（半成品框架）
        """,
    )
    parser.add_argument("--code", required=True, help="股票代码（6 位数字）")
    parser.add_argument("--work-dir", default=os.getcwd(), help="工作目录，默认为当前目录")
    parser.add_argument("--company-name", default=None, help="公司名称（可选，自动从 profile 读取）")
    args = parser.parse_args()

    code = str(args.code).zfill(6)
    work_dir = os.path.abspath(args.work_dir)
    raw_dir = Path(work_dir) / "raw" / "company" / code

    # 读取 raw 数据
    profile = load_json(raw_dir / "profile.json")
    financial = load_json(raw_dir / "financial.json")
    valuation = load_json(raw_dir / "valuation.json")
    reports = load_json(raw_dir / "reports.json")

    print(f"[company_analysis] 代码: {code}")
    print(f"  profile.json:   {'✓' if profile else '✗'}")
    print(f"  financial.json: {'✓' if financial else '✗'}")
    print(f"  valuation.json: {'✓' if valuation else '✗'}")
    print(f"  reports.json:   {'✓' if reports else '✗'}")

    company_name = args.company_name or profile.get("name", code)
    report_list = reports.get("reports", [])
    sources_used = reports.get("sources_used", [])
    source_stats = reports.get("source_stats", {})

    # 构建半成品框架
    analysis = {
        "mode": "company",
        "code": code,
        "company_name": company_name,
        "fetch_time": datetime.now().strftime("%Y-%m-%d"),
        "time_range": reports.get("time_range", "未知"),
        "source_report_count": len(report_list),
        "sources_used": sources_used,
        "source_stats": source_stats,

        # ====== AI 需要手动补全的文本字段（占位符） ======
        "one_sentence_view": "【待补充】一句话核心研究逻辑",

        "chain_positioning": "【待补充】公司产业链定位文本描述（200-300字）",

        "chain_flow": [
            {"title": "上游", "desc": "【待补充】", "highlight": False},
            {"title": f"中游 · {company_name}", "desc": "【待补充】", "highlight": True},
            {"title": "下游", "desc": "【待补充】", "highlight": False},
        ],

        "key_theme_relation": {
            "theme": "【待补充】核心概念",
            "summary": "【待补充】一句话说明关系",
            "points": ["要点1", "要点2"],
        },

        "growth_drivers": [
            {"driver": "【待补充】", "impact": "高", "note": "说明"},
            {"driver": "【待补充】", "impact": "中", "note": "说明"},
        ],

        "business_breakdown": {
            "description": "【待补充】业务结构说明",
            "segments": [
                {"name": "业务线1", "share": "~X%", "note": "说明"},
                {"name": "业务线2", "share": "~X%", "note": "说明"},
            ],
        },

        "competitive_comparison": {
            "position_summary": "【待补充】市场定位",
            "global_companies": [
                {"name": "海外对标", "tag": "全球", "position": "【待补充】", "vs": "【待补充】"},
            ],
            "china": [
                {"name": "国内对标", "position": "【待补充】", "vs": "【待补充】"},
            ],
        },

        "profit_logic": [
            "【待补充】盈利驱动1",
            "【待补充】盈利驱动2",
        ],

        "evidence_sources": [
            {"level": "A", "content": "【待补充】", "source": "年报/公告"},
            {"level": "B", "content": "【待补充】", "source": "券商研报"},
        ],

        "real_bottlenecks": [
            {"bottleneck": "【待补充】", "detail": "具体说明"},
        ],

        "key_metrics": [
            {"metric": "【待补充】", "target": "目标值", "why": "为什么关注"},
        ],

        "research_path": "【待补充】一句话研究路径",

        # ====== 自动填充的结构化数据 ======
        "company_identity": build_identity(profile, valuation),
        "financial_snapshot": build_financial_snapshot(financial),

        "risks": [
            "【待补充】风险1",
            "【待补充】风险2",
        ],
    }

    # 输出
    analysis_dir = Path(work_dir) / "analysis" / "company" / code
    analysis_dir.mkdir(parents=True, exist_ok=True)
    output_path = analysis_dir / "analysis.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # 校验：统计待补充字段数
    json_str = json.dumps(analysis, ensure_ascii=False)
    pending_count = json_str.count("【待补充】")

    print(f"\n[完成] 分析框架已输出: {output_path}")
    print(f"  文件大小: {len(json_str):,} 字节")
    print(f"  自动填充字段: company_identity ({len(analysis['company_identity'])} 项)")
    print(f"                  financial_snapshot ({len(analysis['financial_snapshot'])} 项)")
    print(f"                  sources ({len(sources_used)} 源)")
    print(f"  【待补充】占位符: {pending_count} 处 — AI 需逐一补全")
    print(f"\n建议补全顺序：")
    print(f"  1. one_sentence_view（5秒看懂核心定位）")
    print(f"  2. chain_positioning + chain_flow（产业链定位）")
    print(f"  3. key_theme_relation（核心概念关系）")
    print(f"  4. growth_drivers（增量驱动）")
    print(f"  5. business_breakdown（业务拆分）")
    print(f"  6. competitive_comparison（竞争对比）")
    print(f"  7. profit_logic（盈利逻辑）")
    print(f"  8. real_bottlenecks（真正卡点）")
    print(f"  9. evidence_sources（证据来源）")
    print(f"  10. key_metrics（关键指标）")
    print(f"  11. research_path（研究路径）")
    print(f"  12. risks（风险）")


if __name__ == "__main__":
    main()
