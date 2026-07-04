#!/usr/bin/env python3
"""公司深度分析数据采集模块（v2.3）。

数据源：
  - 同花顺问财 iwencai（需 IWENCAI_API_KEY）：公司基本信息 + 财务指标（主力）
  - 腾讯财经 qt.gtimg.cn（免费公开，不封IP）：实时行情 + 日K线（主力）

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
name               str       iwencai     股票简称（fallback 腾讯财经）
industry           str       iwencai     所属行业
market             str       推导        sh / sz
listing_date       str       iwencai     上市日期（YYYY-MM-DD）
main_business      str       iwencai     主营产品列表
total_shares       float     iwencai     总股本
float_shares       float     iwencai     流通股本
price              float     腾讯财经    最新价（元）
change_pct         float     腾讯财经    涨跌幅（%）
change_amt         float     腾讯财经    涨跌额（元）
open               float     腾讯财经    今开
high               float     腾讯财经    最高
low                float     腾讯财经    最低
last_close         float     腾讯财经    昨收
market_cap         float     腾讯财经    总市值（亿元，兼容旧的元格式）
float_mcap         float     腾讯财经    流通市值（亿元）
pe_ttm             float     腾讯财经    市盈率 TTM
pe_static          float     腾讯财经    市盈率（静态）
pb                 float     腾讯财经    市净率
turnover_pct       float     腾讯财经    换手率（%）
amplitude_pct      float     腾讯财经    振幅（%）
vol_ratio          float     腾讯财经    量比
amount_wan         float     腾讯财经    成交额（万元）
limit_up           float     腾讯财经    涨停价
limit_down         float     腾讯财经    跌停价
roe                float     iwencai     净资产收益率(%)
revenue_yoy        float     iwencai     营收同比(%)
profit_yoy         float     iwencai     净利润同比(%)
gross_margin       float     iwencai     毛利率(%)
net_margin         float     iwencai     净利率(%)
basic_eps          float     iwencai     基本每股收益
bvps               float     iwencai     每股净资产
kline              list      腾讯财经    [{date,open,close,high,low,volume},...]
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
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="


def _get_api_key():
    key = os.environ.get("IWENCAI_API_KEY", "")
    return key


def _parse_market(code):
    code = str(code).zfill(6)
    if code.startswith(("60", "68")):
        return "sh"
    elif code.startswith("8"):
        return "bj"
    elif code.startswith(("00", "30", "002", "003")):
        return "sz"
    return "unknown"


# ---------- 腾讯财经行情 ----------

def tencent_quote(codes):
    """批量获取腾讯财经实时行情。

    腾讯财经 API（qt.gtimg.cn）：
      - HTTP GET，GBK 编码，~ 分隔 88 个字段
      - 不封 IP，无需 Key
      - 支持个股、指数、ETF

    Args:
        codes: 股票代码列表，如 ["688017", "300476", "002463"]

    Returns:
        {code: {...字段...}} 字典，字段包含 name/price/pe_ttm/pb/mcap_yi 等
    """
    prefixed = []
    for c in codes:
        m = _parse_market(c)
        if m == "bj":
            prefixed.append(f"bj{c}")
        elif m == "sh":
            prefixed.append(f"sh{c}")
        else:
            prefixed.append(f"sz{c}")

    url = TENCENT_QUOTE_URL + ",".join(prefixed)
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode("gbk")
    except Exception as e:
        print(f"  [腾讯财经] 请求失败: {e}")
        return {}

    result = {}
    for line in data.strip().split(";"):
        if not line.strip() or "=" not in line or '"' not in line:
            continue
        key = line.split("=")[0].split("_")[-1]
        vals = line.split('"')[1].split("~")
        if len(vals) < 53:
            continue
        code = key[2:]
        result[code] = {
            "name":          vals[1],
            "price":         float(vals[3]) if vals[3] else 0,
            "last_close":    float(vals[4]) if vals[4] else 0,
            "open":          float(vals[5]) if vals[5] else 0,
            "high":          float(vals[33]) if vals[33] else 0,
            "low":           float(vals[34]) if vals[34] else 0,
            "change_amt":    float(vals[31]) if vals[31] else 0,
            "change_pct":    float(vals[32]) if vals[32] else 0,
            "amount_wan":    float(vals[37]) if vals[37] else 0,
            "turnover_pct":  float(vals[38]) if vals[38] else 0,
            "pe_ttm":        float(vals[39]) if vals[39] else 0,
            "amplitude_pct": float(vals[43]) if vals[43] else 0,
            "mcap_yi":       float(vals[44]) if vals[44] else 0,
            "float_mcap_yi": float(vals[45]) if vals[45] else 0,
            "pb":            float(vals[46]) if vals[46] else 0,
            "limit_up":      float(vals[47]) if vals[47] else 0,
            "limit_down":    float(vals[48]) if vals[48] else 0,
            "vol_ratio":     float(vals[49]) if vals[49] else 0,
            "pe_static":     float(vals[52]) if vals[52] else 0,
        }
    return result


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
    """获取公司基本信息——问财（基本面）+ 腾讯财经（行情主力）。"""
    code_str = str(code).zfill(6)

    # ====== 1. 问财：公司基本信息 ======
    name = code_str
    industry = ""
    listing_date = ""
    main_business = ""
    total_shares = None
    float_shares = None

    q1 = f"{code_str} 股票简称 所属行业 上市日期 总股本 流通股本 主营产品"
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

    # ====== 2. 腾讯财经：实时行情（替代东财 push2） ======
    tq = tencent_quote([code_str])
    tx = tq.get(code_str, {})

    if tx:
        # 腾讯财经的名称通常比问财更规范，且不含日期后缀
        if name == code_str:
            name = tx.get("name", code_str) or code_str
        price = tx.get("price", 0) or None
        change_pct = tx.get("change_pct")
        change_amt = tx.get("change_amt")
        open_price = tx.get("open")
        high_price = tx.get("high")
        low_price = tx.get("low")
        last_close = tx.get("last_close")
        pe_ttm = tx.get("pe_ttm")
        pe_static = tx.get("pe_static")
        pb = tx.get("pb")
        market_cap_yi = tx.get("mcap_yi")      # 亿元
        float_mcap_yi = tx.get("float_mcap_yi") # 亿元
        turnover_pct = tx.get("turnover_pct")
        amplitude_pct = tx.get("amplitude_pct")
        vol_ratio = tx.get("vol_ratio")
        amount_wan = tx.get("amount_wan")
        limit_up = tx.get("limit_up")
        limit_down = tx.get("limit_down")
        # 市值统一转为元（与现有 valuation.json 兼容）
        market_cap = market_cap_yi * 1e8 if market_cap_yi else None
    else:
        price = None
        change_pct = None
        change_amt = None
        open_price = None
        high_price = None
        low_price = None
        last_close = None
        pe_ttm = None
        pe_static = None
        pb = None
        market_cap = None
        market_cap_yi = None
        float_mcap_yi = None
        turnover_pct = None
        amplitude_pct = None
        vol_ratio = None
        amount_wan = None
        limit_up = None
        limit_down = None

    return {
        "code": code_str,
        "name": name,
        "market": _parse_market(code_str),
        "industry": industry,
        "listing_date": listing_date,
        "main_business": main_business,
        "price": price,
        "change_pct": change_pct,
        "change_amt": change_amt,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "last_close": last_close,
        "total_shares": total_shares,
        "float_shares": float_shares,
        "market_cap": market_cap,           # 元（兼容旧格式）
        "market_cap_yi": market_cap_yi,     # 亿元（新增）
        "float_mcap_yi": float_mcap_yi,     # 流通市值·亿元（新增）
        "pe_ttm": pe_ttm,
        "pe_static": pe_static,
        "pb": pb,
        "turnover_pct": turnover_pct,
        "amplitude_pct": amplitude_pct,
        "vol_ratio": vol_ratio,
        "amount_wan": amount_wan,
        "limit_up": limit_up,
        "limit_down": limit_down,
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
    """获取近 N 个交易日 K 线数据（腾讯财经 web.ifzq.gtimg.cn）。

    腾讯财经 K 线接口：
      GET https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,,,{days},qfq
      返回 JSON，每条 K 线格式：[date, open, close, high, low, volume]
      前缀规则：60xxxx/68xxxx → sh，00xxxx/30xxxx → sz
    """
    code_str = str(code).zfill(6)
    m = _parse_market(code_str)
    prefix = "sh" if m in ("sh", "bj") else "sz"
    param = f"{prefix}{code_str},day,,,{days},qfq"
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={param}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        stock_data = data.get("data", {}).get(f"{prefix}{code_str}", {})
        klines_raw = stock_data.get("qfqday", []) or stock_data.get("day", [])
    except Exception:
        return []

    klines = []
    for item in klines_raw:
        if len(item) >= 6:
            klines.append({
                "date": item[0],
                "open": float(item[1]),
                "close": float(item[2]),
                "high": float(item[3]),
                "low": float(item[4]),
                "volume": int(float(item[5])),
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
    print(f"[公司采集] 腾讯财经行情: 免费公开，不封IP")
    print(f"{'='*60}")

    # 1. Profile（问财基本面 + 腾讯财经行情）
    print("  [1/4] 获取公司基本信息...")
    profile = fetch_profile(code)
    print(f"        名称: {profile['name']}  行业: {profile.get('industry', '?')}")
    print(f"        股价: {profile.get('price')}  市值: {_fmt_cap(profile.get('market_cap'))}")
    print(f"        PE(TTM): {profile.get('pe_ttm')}  PB: {profile.get('pb')}  换手率: {profile.get('turnover_pct')}%")

    with open(raw_dir / "profile.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    # 2. Financial（问财）
    print("  [2/4] 获取财务指标...")
    financial = fetch_financial(code)
    print(f"        ROE: {financial.get('roe')}%  毛利率: {financial.get('gross_margin')}%")
    print(f"        营收同比: {financial.get('revenue_yoy')}%  净利润同比: {financial.get('profit_yoy')}%")

    with open(raw_dir / "financial.json", "w", encoding="utf-8") as f:
        json.dump(financial, f, ensure_ascii=False, indent=2)

    # 3. Valuation（腾讯财经数据）
    print("  [3/4] 保存估值数据...")
    valuation = {
        "code": code,
        "name": profile.get("name", code),
        "price": profile.get("price"),
        "change_pct": profile.get("change_pct"),
        "change_amt": profile.get("change_amt"),
        "open": profile.get("open"),
        "high": profile.get("high"),
        "low": profile.get("low"),
        "last_close": profile.get("last_close"),
        "pe_ttm": profile.get("pe_ttm"),
        "pe_static": profile.get("pe_static"),
        "pb": profile.get("pb"),
        "market_cap": profile.get("market_cap"),
        "market_cap_yi": profile.get("market_cap_yi"),
        "float_mcap_yi": profile.get("float_mcap_yi"),
        "turnover_pct": profile.get("turnover_pct"),
        "amplitude_pct": profile.get("amplitude_pct"),
        "vol_ratio": profile.get("vol_ratio"),
        "amount_wan": profile.get("amount_wan"),
        "limit_up": profile.get("limit_up"),
        "limit_down": profile.get("limit_down"),
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
    print(f"  profile.json     — 基本信息（问财+腾讯财经行情）")
    print(f"  financial.json   — 财务指标（问财）")
    print(f"  valuation.json   — 估值快照（腾讯财经行情）")
    print(f"  kline.json       — 日K线·前复权（腾讯财经，{len(kline)} 日）")

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
    parser = argparse.ArgumentParser(description="公司深度分析数据采集（问财+腾讯财经双源）")
    parser.add_argument("--code", required=True, help="股票代码（6 位数字，如 300750）")
    parser.add_argument("--output-dir", default=None, help="输出根目录，默认当前工作目录")
    args = parser.parse_args()

    code = args.code
    output_dir = args.output_dir or os.getcwd()

    result = collect_company(code, output_dir)
    return result


if __name__ == "__main__":
    main()
