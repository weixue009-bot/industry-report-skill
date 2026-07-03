#!/usr/bin/env python3
"""公司深度分析数据采集模块（v2.1）。

数据源：
  - 同花顺问财 iwencai（需 IWENCAI_API_KEY）：基本面 + 财务指标（主力）
  - 东方财富 push2（免费公开）：行情快照 + K线（辅助）

职责：
  - fetch_profile()   → raw/company/{代码}/profile.json
  - fetch_financial() → raw/company/{代码}/financial.json
  - fetch_valuation() → raw/company/{代码}/valuation.json
  - fetch_kline()     → raw/company/{代码}/kline.json

统一直播字段声明：
=====================================================================
字段名             类型      来源        说明
---------------------------------------------------------------------
code               str       参数传入    股票代码（6 位数字）
name               str       iwencai     股票简称
industry           str       iwencai     所属行业
market             str       推导        sh / sz
total_shares       float     iwencai     总股本
float_shares       float     iwencai     流通股本
market_cap         float     em/iwencai  总市值（元）
pe_ttm             float     iwencai     市盈率 TTM
pb                 float     iwencai     市净率
roe                float     iwencai     净资产收益率(%)
revenue_yoy        float     iwencai     营收同比(%)
profit_yoy         float     iwencai     净利润同比(%)
gross_margin       float     iwencai     毛利率(%)
net_margin         float     iwencai     净利率(%)
basic_eps          float     iwencai     基本每股收益
bvps               float     iwencai     每股净资产
kline              list      东财 push2  [{date,open,close,high,low,volume,amount},...]
=====================================================================
"""

import argparse
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------- 常量 ----------

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
IWENCAI_URL = "https://openapi.iwencai.com/v1/query2data"
IWENCAI_SKILL_ID = "hithink-market-query"
IWENCAI_SKILL_VERSION = "1.0.0"


def _get_api_key():
    key = os.environ.get("IWENCAI_API_KEY", "")
    return key


def _parse_market(code):
    code = str(code).zfill(6)
    if code.startswith(("60", "68")):
        return "sh"
    elif code.startswith(("00", "30", "002", "003")):
        return "sz"
    return "unknown"


def _secid(code):
    m = _parse_market(code)
    return f"{1 if m == 'sh' else 0}.{code}"


# ---------- 东财工具 ----------

def _em_get(url, params=None, referer="https://data.eastmoney.com/", timeout=15, retries=2):
    if params:
        qs = urllib.parse.urlencode(params)
        url = f"{url}?{qs}"
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt < retries:
                time.sleep(1 + attempt)
            else:
                raise


# ---------- 同花顺问财工具 ----------

def _iwencai_query(query, timeout=30):
    """调用同花顺问财 query2data API，返回 datas 列表的第一条记录（dict）。失败返回 {}。"""
    api_key = _get_api_key()
    if not api_key:
        return {}
    body = json.dumps({
        "query": query,
        "page": "1",
        "limit": "3",
        "is_cache": "1",
        "expand_index": "true",
    }).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": IWENCAI_SKILL_ID,
        "X-Claw-Skill-Version": IWENCAI_SKILL_VERSION,
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }
    try:
        req = urllib.request.Request(IWENCAI_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        datas = result.get("datas", [])
        return datas[0] if datas else {}
    except Exception as e:
        print(f"  [iwencai] 查询失败: {e}")
        return {}


def _extract_number(d, keys):
    """从 iwencai 返回的 dict 中，按优先级取第一个非空数字。"""
    for k in keys:
        v = d.get(k)
        if v is not None and v != "":
            try:
                return float(v)
            except (ValueError, TypeError):
                continue
    return None


def _extract_str(d, keys):
    for k in keys:
        v = d.get(k)
        if v and isinstance(v, str) and v.strip():
            return v.strip()
    return ""


# ---------- 数据采集函数 ----------

def fetch_profile(code):
    """获取公司基本信息——主要依赖问财，辅助东财行情。"""
    code_str = str(code).zfill(6)
    name = code_str

    # 1. 问财查询：基本面
    q1 = f"{code_str} 股票简称 所属行业 上市日期 总股本 流通股本 主营产品 市盈率 市净率 总市值"
    d1 = _iwencai_query(q1)
    if d1:
        name = d1.get("股票简称", code_str)
        industry_list = d1.get("所属同花顺行业", [])
        industry = " — ".join(industry_list) if isinstance(industry_list, list) else str(industry_list)
        listing_date_raw = d1.get("上市日期", "")
        listing_date = f"{str(listing_date_raw)[:4]}-{str(listing_date_raw)[4:6]}-{str(listing_date_raw)[6:8]}" if len(str(listing_date_raw)) >= 8 else str(listing_date_raw)
        main_biz_list = d1.get("主营产品", [])
        main_business = ", ".join(main_biz_list[:8]) if isinstance(main_biz_list, list) else str(main_biz_list)

        total_shares = d1.get("总股本[20260703]", None) or _extract_number(d1,
            [k for k in d1 if "总股本" in k and "流通" not in k])
        float_shares = d1.get("流通股本[20260703]", None) or _extract_number(d1,
            [k for k in d1 if "流通股本" in k])

        pe_ttm = _extract_number(d1, [k for k in d1 if "市盈率ttm" in k.lower() or "最新市盈率ttm" in k.replace(" ","").lower()])
        if pe_ttm is None:
            pe_ttm = d1.get("最新市盈率ttm") or d1.get("最新市盈率TTM")
            if pe_ttm is not None:
                pe_ttm = float(pe_ttm)
        pb = d1.get("最新市净率") or d1.get("市净率[20260703]")
        if pb is not None:
            pb = float(pb)
        market_cap_from_iwencai = d1.get("总市值[20260703]", None) or _extract_number(d1,
            [k for k in d1 if "总市值" in k])
    else:
        industry = ""
        listing_date = ""
        main_business = ""
        total_shares = None
        float_shares = None
        pe_ttm = None
        pb = None
        market_cap_from_iwencai = None

    # 2. 东财 push2 辅助：行情快照
    price = None
    change_pct = None
    market_cap = market_cap_from_iwencai
    volume = None
    amount = None
    high_price = None
    low_price = None
    open_price = None

    try:
        secid = _secid(code)
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f116,f117,f170",
            "ut": "fa5fd1943c7b386f172d6893dbf55f6e",
            "wbp2u": "|0|0|0|web",
        }
        em_data = _em_get(url, params)
        em = em_data.get("data", {}) or {}
        price = em.get("f43", 0) / 100 if em.get("f43") else None
        change_pct = em.get("f170")
        if market_cap is None:
            market_cap = em.get("f116") or em.get("f117")
        volume = em.get("f47")
        amount = em.get("f48")
        high_price = em.get("f44", 0) / 100 if em.get("f44") else None
        low_price = em.get("f45", 0) / 100 if em.get("f45") else None
        open_price = em.get("f46", 0) / 100 if em.get("f46") else None

        # 如果问财没有取到名称，再试东财 f58
        if name == code_str:
            name = em.get("f58", code_str) or code_str
    except Exception as e:
        print(f"  [东财] 行情快照获取失败: {e}")

    return {
        "code": code_str,
        "name": name,
        "market": _parse_market(code_str),
        "industry": industry,
        "listing_date": listing_date,
        "main_business": main_business,
        "price": price,
        "change_pct": change_pct,
        "total_shares": total_shares,
        "float_shares": float_shares,
        "market_cap": market_cap,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "volume": volume,
        "amount": amount,
        "high": high_price,
        "low": low_price,
        "open": open_price,
    }


def fetch_financial(code):
    """获取最新一期财务指标快照——基于问财查询。"""
    code_str = str(code).zfill(6)

    q = (f"{code_str} 资产负债率 总资产 流动资产 流动负债 每股净资产 "
         f"基本每股收益 净资产收益率roe 营业收入 归母净利润 扣非净利润 "
         f"利润总额 毛利率 净利率 营收增长率 净利润增长率")
    d = _iwencai_query(q)

    if not d:
        return _empty_financial(code_str)

    # 字段名中有日期后缀如 [20260331]，用 contains 匹配
    def _find(keyword):
        for k in d:
            if keyword in k:
                v = d[k]
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return v
        return None

    return {
        "code": code_str,
        "report_date": "2026Q1",
        "basic_eps": _find("基本每股收益"),
        "roe": _find("净资产收益率roe"),
        "gross_margin": _find("销售毛利率"),
        "net_margin": _find("销售净利率"),
        "revenue_yoy": _find("营业收入(同比增长率)"),
        "profit_yoy": _find("归属母公司股东的净利润(同比增长率)"),
        "revenue": _find("营业收入[2"),
        "total_profit": _find("利润总额"),
        "parent_netprofit": _find("归属于母公司所有者的净利润"),
        "bvps": _find("每股净资产"),
        "total_assets": _find("资产总计"),
        "current_assets": _find("流动资产合计"),
        "current_liab": _find("流动负债合计"),
        "debt_ratio": _find("资产负债率"),
        "historical": [],
    }


def _empty_financial(code_str):
    return {
        "code": str(code_str).zfill(6),
        "report_date": "", "basic_eps": None, "roe": None,
        "gross_margin": None, "net_margin": None,
        "revenue_yoy": None, "profit_yoy": None,
        "revenue": None, "total_profit": None,
        "parent_netprofit": None, "bvps": None,
        "total_assets": None, "current_assets": None,
        "current_liab": None, "debt_ratio": None,
        "historical": [],
    }


def fetch_kline(code, days=250):
    """获取近 N 个交易日 K 线数据。"""
    secid = _secid(code)
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "end": "20500101",
        "lmt": str(days),
        "ut": "fa5fd1943c7b386f172d6893dbf55f6e",
    }
    try:
        data = _em_get(url, params)
        klines_raw = (data.get("data", {}) or {}).get("klines", []) or []
    except Exception:
        return []

    klines = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) >= 7:
            klines.append({
                "date": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": int(parts[5]),
                "amount": float(parts[6]),
            })
    return klines


# ---------- 综合入口 ----------

def collect_company(code, output_dir):
    code = str(code).zfill(6)
    raw_dir = Path(output_dir) / "raw" / "company" / code
    raw_dir.mkdir(parents=True, exist_ok=True)

    has_api_key = bool(_get_api_key())

    print(f"\n{'='*60}")
    print(f"[公司采集] 代码: {code}")
    print(f"[公司采集] 问财 API Key: {'✓ 已配置' if has_api_key else '✗ 未配置'}")
    print(f"{'='*60}")

    # 1. Profile（问财 + 东财双源）
    print("  [1/4] 获取公司基本信息...")
    profile = fetch_profile(code)
    print(f"        名称: {profile['name']}  行业: {profile.get('industry', '?')}")
    print(f"        市值: {_fmt_cap(profile.get('market_cap'))}  PE(TTM): {profile.get('pe_ttm')}  PB: {profile.get('pb')}")

    with open(raw_dir / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    # 2. Financial（问财）
    print("  [2/4] 获取财务指标...")
    financial = fetch_financial(code)
    print(f"        ROE: {financial.get('roe')}%  毛利率: {financial.get('gross_margin')}%")
    print(f"        营收同比: {financial.get('revenue_yoy')}%  净利润同比: {financial.get('profit_yoy')}%")

    with open(raw_dir / "financial.json", "w", encoding="utf-8") as f:
        json.dump(financial, f, ensure_ascii=False, indent=2)

    # 3. Valuation
    print("  [3/4] 保存估值数据...")
    valuation = {
        "code": code,
        "name": profile.get("name", code),
        "pe_ttm": profile.get("pe_ttm"),
        "pb": profile.get("pb"),
        "market_cap": profile.get("market_cap"),
        "price": profile.get("price"),
        "change_pct": profile.get("change_pct"),
        "volume": profile.get("volume"),
        "amount": profile.get("amount"),
        "high": profile.get("high"),
        "low": profile.get("low"),
        "open": profile.get("open"),
    }
    with open(raw_dir / "valuation.json", "w", encoding="utf-8") as f:
        json.dump(valuation, f, ensure_ascii=False, indent=2)

    # 4. K-line
    print("  [4/4] 获取日K线（近一年）...")
    kline = fetch_kline(code, days=250)
    print(f"        共 {len(kline)} 个交易日 K 线")

    with open(raw_dir / "kline.json", "w", encoding="utf-8") as f:
        json.dump(kline, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 数据已保存至: {raw_dir}")
    print(f"  profile.json     — 基本信息")
    print(f"  financial.json   — 财务指标")
    print(f"  valuation.json   — 估值快照")
    print(f"  kline.json       — 日K线 ({len(kline)} 日)")

    return {
        "code": code,
        "name": profile.get("name", code),
        "dir": str(raw_dir),
    }


def _fmt_cap(cap):
    if cap is None:
        return "N/A"
    cap = float(cap)
    if cap >= 1e12:
        return f"{cap/1e12:.2f}万亿"
    return f"{cap/1e8:.2f}亿"


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(description="公司深度分析数据采集（问财+东财双源）")
    parser.add_argument("--code", required=True, help="股票代码（6 位数字，如 300750）")
    parser.add_argument("--output-dir", default=None, help="输出根目录，默认当前工作目录")
    args = parser.parse_args()

    code = args.code
    output_dir = args.output_dir or os.getcwd()

    result = collect_company(code, output_dir)
    return result


if __name__ == "__main__":
    main()
