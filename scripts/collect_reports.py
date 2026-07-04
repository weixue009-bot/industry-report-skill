#!/usr/bin/env python3
"""投资研究数据采集脚本（三数据源·双模式版）。

支持两种模式：
  --mode industry  行业研报采集（默认）
  --mode company   个股研报采集

数据源：
1. iwencai report-search（需 IWENCAI_API_KEY）
2. 东方财富 reportapi（免费公开接口，无需 Key）
3. 发现报告 fxbaogao.com（免费公开接口，无需 Key）

输出约定：
  行业模式 → raw/industry/{行业名}/
  公司模式 → raw/company/{代码}/
"""

import argparse
import html
import json
import os
import random
import re
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 数据源一：iwencai report-search（需 API Key）
# ============================================================

SKILL_ID = "report-search"
SKILL_VERSION = "1.0.0"
DEFAULT_BASE_URL = "https://openapi.iwencai.com"
DEFAULT_ENDPOINT = "/v1/comprehensive/search"
DEFAULT_TIMEOUT = 30

MISSING_KEY_NOTICE = """首次使用 - 获取 API Key
所有技能都需要 IWENCAI_API_KEY 环境变量才能使用。如果用户尚未配置，按以下步骤引导：
步骤 1：获取 API Key
在浏览器内打同花顺i问财SkillHub页面：https://www.iwencai.com/skillhub
步骤 2：登录
步骤 3：点击具体的Skill，打开弹窗查看详情，在安装方式-Agent用户-找到您的IWENCAI_API_KEY这一段，复制
步骤 4：配置环境变量"""

# ============================================================
# 行业数据源：hithink-industry-query（同花顺官方行业数据 skill）
# ============================================================

INDUSTRY_SKILL_ID = "hithink-industry-query"
INDUSTRY_SKILL_VERSION = "1.0.0"

def _get_api_key():
    return os.environ.get("IWENCAI_API_KEY", "")


def call_hithink_industry(query, api_key=None, timeout=15):
    """调用同花顺官方 hithink-industry-query skill 查询行业结构化数据。
    
    支持：行业估值/财务/行情/板块排名等查询。
    JSON 响应结构：{"datas": [...], "code_count": N, ...}
    """
    key = api_key or _get_api_key()
    if not key:
        return {"error": "API Key 未设置"}
    body = json.dumps({
        "query": query,
        "page": "1",
        "limit": "5",
        "is_cache": "1",
        "expand_index": "true",
    }, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": INDUSTRY_SKILL_ID,
        "X-Claw-Skill-Version": INDUSTRY_SKILL_VERSION,
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }
    url = "https://openapi.iwencai.com/v1/query2data"
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def fetch_industry_stats(industry, segments, api_key=None):
    """采集行业结构化数据（估值/行情/排名等），返回 dict。
    
    供 Step 4 AI 分析阶段使用，作为评分和判断的量化依据。
    """
    api_key = api_key or _get_api_key()
    if not api_key:
        return {"error": "API Key 未设置，无法采集行业统计数据"}
    
    results = {}
    
    # 1. 行业整体估值
    q1 = f"{industry} 行业市盈率 行业市净率 行业排名 总市值"
    r1 = call_hithink_industry(q1, api_key=api_key)
    results["valuation"] = r1.get("datas", [])
    
    # 2. 板块行情
    q2 = f"{industry} 板块涨跌幅 板块资金流入 主力资金"
    r2 = call_hithink_industry(q2, api_key=api_key)
    results["momentum"] = r2.get("datas", [])
    
    # 3. 按 segment 逐个查估值
    results["seg_valuation"] = {}
    for seg in segments[:3]:  # 最多查 3 个环节
        q3 = f"{seg} {industry} 市盈率 毛利率 营收增长率"
        r3 = call_hithink_industry(q3, api_key=api_key)
        seg_datas = r3.get("datas", [])
        if seg_datas:
            results["seg_valuation"][seg] = seg_datas[0]
        time.sleep(0.5)
    
    return results


def build_headers(api_key):
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Claw-Call-Type": "normal",
        "X-Claw-Skill-Id": SKILL_ID,
        "X-Claw-Skill-Version": SKILL_VERSION,
        "X-Claw-Plugin-Id": "none",
        "X-Claw-Plugin-Version": "none",
        "X-Claw-Trace-Id": secrets.token_hex(32),
    }


def call_iwencai(query, size, api_key, base_url, timeout):
    """调用 iwencai report-search API。"""
    url = f"{base_url.rstrip('/')}/{DEFAULT_ENDPOINT.lstrip('/')}"
    body = json.dumps({
        "query": query,
        "channels": ["report"],
        "app_id": "AIME_SKILL",
        "size": size,
    }, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=body, headers=build_headers(api_key), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None
    except Exception as exc:
        return -1, None


# ============================================================
# 数据源二：东方财富 reportapi（免费公开接口）
# ============================================================

# 东财防封配置
EM_MIN_INTERVAL = 1.0  # 最小间隔（秒）
EM_SESSION = None
_em_last_call = [0.0]
EM_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
REPORT_API = "https://reportapi.eastmoney.com/report/list"
PDF_TPL = "https://pdf.dfcfw.com/pdf/H3_{info_code}_1.pdf"


def _em_get(url, params=None, timeout=15):
    """东财统一请求入口：自动节流 + 复用 session + 默认 UA。"""
    global EM_SESSION
    if EM_SESSION is None:
        EM_SESSION = __import__("requests").Session()
        EM_SESSION.headers.update({"User-Agent": EM_UA})

    wait = EM_MIN_INTERVAL - (time.time() - _em_last_call[0])
    if wait > 0:
        time.sleep(wait + random.uniform(0.1, 0.5))

    try:
        resp = EM_SESSION.get(
            url, params=params,
            headers={"Referer": "https://data.eastmoney.com/",
                     "User-Agent": EM_UA},
            timeout=timeout,
        )
        return resp
    finally:
        _em_last_call[0] = time.time()


def call_eastmoney_industry_reports(industry, months, page_size=100):
    """调用东财 reportapi 获取行业研报（qType=1），按东财行业分类字段过滤。
    
    旧版用 industry_keywords 对标题做子串匹配，导致很多研报因标题不含指定关键词而被漏掉。
    东财每条记录自带 industryName 字段（如"医药 — 化学制药"），用它做分类过滤更精准。
    
    Args:
        industry: 行业名称，用于匹配东财 record 的 industryName 字段
        months: 时间范围（月），东财 API 在 URL 上严格按 beginTime 过滤
        page_size: 每页条数，最大100
    
    Returns:
        解析后的研报列表（统一格式），最多 page_size * max_pages 条
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    begin = start_date.strftime("%Y-%m-%d")

    # 行业名 → 东财 industryName 匹配关键词（宽泛匹配，宁多勿漏）
    _INDUSTRY_NAME_KEYWORDS = {
        "创新药": ["医药", "生物", "创新", "CXO", "CRO", "CDMO", "ADC", "抗体", "PD-1", "肿瘤", "抗癌", "免疫", "靶向"],
        "机器人": ["机器人", "自动化", "工业母机", "数控", "伺服", "减速器", "传感器"],
        "半导体": ["半导体", "芯片", "集成电路", "晶圆", "封装", "EDA", "光刻"],
        "新能源": ["新能源", "光伏", "风电", "储能", "锂电", "电池", "碳中和"],
        "人工智能": ["人工智能", "AI", "算力", "大模型", "芯片", "GPU", "数据中心"],
        "汽车": ["汽车", "新能源车", "电动车", "智能驾驶", "自动驾驶", "车联网"],
    }
    name_kws = _INDUSTRY_NAME_KEYWORDS.get(industry, [industry])

    all_records = []
    max_pages = 3

    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*",
            "pageSize": str(page_size),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": begin,
            "endTime": "2030-01-01",
            "pageNo": str(page),
            "fields": "",
            "qType": "1",
        }

        try:
            r = _em_get(REPORT_API, params=params, timeout=30)
            if r.status_code != 200:
                print(f"  东财 API 返回状态码 {r.status_code}")
                break

            d = r.json()
            rows = d.get("data") or []
            if not rows:
                break

            # 按东财行业分类字段 + 标题关键词双重过滤
            for item in rows:
                title = item.get("title", "") or ""
                industry_name = item.get("industryName", "") or ""
                
                # industryName 匹配（最可靠）
                name_match = any(kw.lower() in industry_name.lower() for kw in name_kws)
                # 标题匹配（补充）
                title_match = any(kw.lower() in title.lower() for kw in name_kws)
                
                if not name_match and not title_match:
                    continue
                pub_time = item.get("publishDate", "")
                if isinstance(pub_time, str):
                    pub_time = pub_time[:10]

                record = {
                    "uid": f"em_{item.get('infoCode', '')}",
                    "title": title.strip(),
                    "summary": "",
                    "content": "",
                    "institution": (item.get("orgSName") or "").strip(),
                    "analyst": "",
                    "date": pub_time,
                    "url": "",
                    "rating": (item.get("emRatingName") or "").strip(),
                    "source": "eastmoney",
                    "info_code": item.get("infoCode", ""),
                    "industry_name": item.get("industryName", ""),
                    "industry_code": item.get("industryCode", ""),
                    "attach_pages": item.get("attachPages", 0),
                    "eps_this_year": item.get("predictThisYearEps") or None,
                    "eps_next_year": item.get("predictNextYearEps") or None,
                    "eps_next_two_year": item.get("predictNextTwoYearEps") or None,
                }
                all_records.append(record)

            if page >= (d.get("TotalPage", 1) or 1):
                break

        except Exception as exc:
            print(f"  东财 API 请求异常: {exc}")
            break

    return all_records


def call_eastmoney_stock_reports(code, months, page_size=50):
    """调用东财 reportapi 获取个股研报（qType=0）。"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    begin = start_date.strftime("%Y-%m-%d")

    all_records = []
    max_pages = 3

    for page in range(1, max_pages + 1):
        params = {
            "industryCode": "*",
            "pageSize": str(page_size),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": begin,
            "endTime": "2030-01-01",
            "pageNo": str(page),
            "fields": "",
            "qType": "0",
            "orgCode": "",
            "code": code,
            "rcode": "",
            "p": str(page),
            "pageNum": str(page),
            "pageNumber": str(page),
        }

        try:
            r = _em_get(REPORT_API, params=params, timeout=30)
            if r.status_code != 200:
                break

            d = r.json()
            rows = d.get("data") or []
            if not rows:
                break

            for item in rows:
                pub_time = item.get("publishDate", "")
                if isinstance(pub_time, str):
                    pub_time = pub_time[:10]

                record = {
                    "uid": f"em_{item.get('infoCode', '')}",
                    "title": (item.get("title") or "").strip(),
                    "summary": "",
                    "content": "",
                    "institution": (item.get("orgSName") or "").strip(),
                    "analyst": "",
                    "date": pub_time,
                    "url": "",
                    "rating": (item.get("emRatingName") or "").strip(),
                    "source": "eastmoney",
                    "info_code": item.get("infoCode", ""),
                    "industry_name": item.get("indvInduName", ""),
                    "eps_this_year": item.get("predictThisYearEps") or None,
                    "eps_next_year": item.get("predictNextYearEps") or None,
                    "eps_next_two_year": item.get("predictNextTwoYearEps") or None,
                }
                all_records.append(record)

            if page >= (d.get("TotalPage", 1) or 1):
                break

        except Exception as exc:
            print(f"  东财个股 API 请求异常: {exc}")
            break

    return all_records


def check_eastmoney_available():
    """检测东财 reportapi 是否可访问。"""
    try:
        r = _em_get(REPORT_API, params={
            "pageSize": "1", "pageNo": "1",
            "beginTime": "2026-01-01", "endTime": "2030-01-01",
            "qType": "1", "industryCode": "*",
            "industry": "*", "rating": "*", "ratingChange": "*",
            "fields": "",
        }, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


# ============================================================
# 统一的报告解析和去重
# ============================================================

# 统一 report record 字段定义（所有数据源统一输出此结构）：
#   uid               str   唯一标识（iwencai 用 uid，东财用 em_{infoCode}）
#   title             str   研报标题
#   summary           str   摘要（200-300字）
#   content           str   正文节选（500-2000字，iwencai 的 source_original）
#   institution       str   券商/机构名
#   analyst           str   分析师
#   date              str   发布日期 YYYY-MM-DD
#   url               str   报告原文链接
#   rating            str   投资评级
#   source            str   数据来源："iwencai" | "eastmoney"
#   matched_segment   str   匹配到的产业链环节名（采集后设置）
#   -- 东财独有字段 --
#   info_code         str   东财 infoCode（用于拼 PDF URL）
#   industry_name     str   东财行业分类名
#   industry_code     str   东财行业代码
#   attach_pages      int   PDF 页数
#   eps_this_year     float|None  今年 EPS 预测
#   eps_next_year     float|None  明年 EPS 预测
#   eps_next_two_year float|None  后年 EPS 预测

def parse_iwencai_report(item):
    """从 iwencai API 返回的单条记录中提取统一字段。"""
    uid = item.get("uid", "") or item.get("report_id", "") or item.get("id", "")
    title = item.get("title", "") or item.get("report_title", "")
    summary = item.get("summary", "") or item.get("abstract", "") or item.get("content", "")

    institution = (
        item.get("institution", "")
        or item.get("org", "")
        or item.get("source", "")
        or item.get("org_name", "")
        or item.get("publisher", "")
    )

    analyst = item.get("analyst", "") or item.get("author", "") or item.get("analyst_name", "")

    publish_time = item.get("publish_time", "")
    if isinstance(publish_time, (int, float)):
        if publish_time > 1e12:
            publish_time = datetime.fromtimestamp(publish_time / 1000)
        else:
            publish_time = datetime.fromtimestamp(publish_time)
        publish_time = publish_time.strftime("%Y-%m-%d")

    url = item.get("url", "") or item.get("link", "") or item.get("report_url", "")
    rating = item.get("rating", "") or item.get("investment_rating", "")
    # 正文节选：500-2000 字，远丰富于 summary（200-300字）
    content = item.get("source_original", "") or item.get("content", "")

    return {
        "uid": uid,
        "title": str(title).strip(),
        "summary": str(summary).strip(),
        "content": str(content).strip(),
        "institution": str(institution).strip(),
        "analyst": str(analyst).strip(),
        "date": str(publish_time).strip(),
        "url": str(url).strip(),
        "rating": str(rating).strip(),
        "source": "iwencai",
    }


# ============================================================
# 数据源三：发现报告 fxbaogao.com（免费公开接口）
# ============================================================

FXBAOGAO_BASE_URL = os.getenv("FXBAOGAO_BASE_URL", "https://api.fxbaogao.com")
FXBAOGAO_UA = "report-search-skill/1.0 (+https://www.fxbaogao.com)"
FXBAOGAO_SSL_NO_VERIFY = os.getenv("FXBAOGAO_SSL_NO_VERIFY", "").lower() in {"1", "true", "yes"}

RELATIVE_TIME_VALUES = {
    "last3day": 3,
    "last7day": 7,
    "last1mon": 30,
    "last3mon": 90,
    "last1year": 365,
}


def _fx_strip_html(value):
    """去掉 HTML 标签，返回纯文本。"""
    if not value:
        return ""
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def _fx_clean_snippet(value):
    cleaned = _fx_strip_html(value)
    return re.sub(r"^[•·]+\s*", "", cleaned)


def check_fxbaogao_available():
    """检测 fxbaogao.com 是否可访问。"""
    try:
        ctx = _build_fx_ssl_context()
        req = urllib.request.Request(
            f"{FXBAOGAO_BASE_URL}/mofoun/report/searchReport/searchNoAuth",
            data=b"{}",
            headers={"Content-Type": "application/json", "User-Agent": FXBAOGAO_UA},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status == 200
    except Exception:
        return False


def _build_fx_ssl_context():
    if FXBAOGAO_SSL_NO_VERIFY:
        return ssl._create_unverified_context()
    return ssl.create_default_context()


def call_fxbaogao_reports(keywords, time_str="last3mon", page_size=20):
    """调用 fxbaogao.com 搜索研报（无需 Key）。
    
    Args:
        keywords: 搜索关键词
        time_str: 相对时间（last3day/last7day/last1mon/last3mon/last1year）
        page_size: 每页条数，最大 100
    
    Returns:
        解析后的研报列表（统一格式）
    """
    payload = json.dumps({
        "keywords": keywords,
        "authors": [],
        "orgNames": [],
        "paragraphSize": 2,
        "startTime": None,
        "endTime": time_str,
        "pageSize": min(page_size, 100),
        "pageNum": 1,
    }, ensure_ascii=False).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": FXBAOGAO_UA,
        "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
    }

    try:
        ctx = _build_fx_ssl_context()
        req = urllib.request.Request(
            f"{FXBAOGAO_BASE_URL}/mofoun/report/searchReport/searchNoAuth",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            raw_data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as exc:
        print(f"[fxbaogao] 请求失败: {exc}")
        return []

    if raw_data.get("code") != 0:
        print(f"[fxbaogao] API 返回错误: {raw_data.get('msg', '')}")
        return []

    data = raw_data.get("data") or {}
    items = data.get("dataList") or []
    records = []

    for item in items:
        doc_id = item.get("docId", "")
        title = _fx_strip_html(item.get("title")) or "无标题"
        org_name = _fx_strip_html(item.get("orgName")) or ""
        authors = item.get("authors") or []
        pub_time = item.get("pubTime")
        pub_time_str = (item.get("pubTimeStr") or "").strip().rstrip("/").replace("/", "-")
        
        # 格式化日期
        if pub_time_str:
            date = pub_time_str
        elif isinstance(pub_time, (int, float)) and pub_time > 0:
            date = datetime.fromtimestamp(pub_time).strftime("%Y-%m-%d")
        else:
            date = ""

        # 取分段摘要作为 summary
        snippets = []
        for p in (item.get("paragraphObjs") or []):
            s = _fx_clean_snippet(p.get("content"))
            if s:
                snippets.append(s)

        record = {
            "uid": f"fx_{doc_id}",
            "title": title,
            "summary": snippets[0] if snippets else "",
            "content": " | ".join(snippets) if snippets else "",
            "institution": org_name,
            "analyst": ", ".join(authors) if authors else "",
            "date": date,
            "url": f"https://www.fxbaogao.com/view?id={doc_id}",
            "rating": "",
            "source": "fxbaogao",
            "info_code": "",
            "industry_name": _fx_strip_html(item.get("industryName")) or "",
            "attach_pages": item.get("pageNum", 0),
        }
        records.append(record)

    return records


# ============================================================
# 去重 + 分类逻辑
# ============================================================


def dedup_reports(reports):
    """去重：先按 uid 去重，再按 title+date 联合去重。"""
    seen_uids = set()
    seen_titles = set()
    result = []

    for r in reports:
        uid = r.get("uid", "")
        if uid and uid in seen_uids:
            continue
        if uid:
            seen_uids.add(uid)

        # 无 uid 时用 title+date 联合去重
        title_date_key = f"{r.get('date', '')}_{r.get('title', '')[:60]}"
        if not uid:
            if title_date_key in seen_titles:
                continue
            seen_titles.add(title_date_key)

        result.append(r)

    return result


def match_segment(report, segments):
    """根据标题关键词匹配产业环节。返回匹配的环节名，无匹配返回 None。
    
    先尝试精确匹配 segment name，再用扩展关键词模糊匹配（用于东财研报）。
    """
    title_lower = report["title"].lower()
    summary_lower = report.get("summary", "").lower()
    content_lower = report.get("content", "").lower()
    combined = title_lower + " " + summary_lower + " " + content_lower

    # 第一轮：精确匹配 segment name
    for seg in segments:
        seg_lower = seg.lower()
        if seg_lower in title_lower or seg_lower in summary_lower:
            return seg

    # 第二轮：扩展关键词模糊匹配（解决东财研报标题不含 segment name 的问题）
    _SEGMENT_KEYWORDS = {
        "化学创新药": ["创新药", "小分子", "靶向", "激酶", "cdk", "egfr", "alk", "kras", "adc"],
        "生物创新药": ["生物药", "抗体", "pd-1", "pd-l1", "ctla-4", "双抗", "单抗", "biotech", "免疫治疗"],
        "CXO产业链": ["cxo", "cro", "cdmo", "研发外包", "生产外包", "药明", "康龙", "凯莱英"],
        "创新中药": ["中药", "经典名方", "中药创新", "天士力", "以岭", "康弘"],
        "原料药": ["原料药", "api", "中间体", "仿制药原料"],
        "ADC/双抗前沿技术": ["adc", "抗体偶联", "双抗", "双特异性", "her2", "trop2", "claudin"],
        "出海型创新药企": ["出海", "海外", "全球", "license", "bd", "fda", "美国", "欧洲", "百济", "信达", "传奇", "商业化"],
        "丝杠": ["丝杠", "行星滚柱", "滚珠丝杠", "tbi", "直线运动"],
        "减速器": ["减速器", "谐波", "rv减速", "哈默纳科", "绿的谐波"],
        "电机": ["电机", "伺服", "空心杯", "无框力矩", "兆威"],
        "传感器": ["传感器", "力传感", "六维力", "触觉", "安培龙"],
        "灵巧手": ["灵巧手", "末端执行器", "手指", "抓取"],
        "具身智能模型": ["具身智能", "vla", "世界模型", "机器人brain"],
    }

    for seg in segments:
        keywords = _SEGMENT_KEYWORDS.get(seg, [])
        for kw in keywords:
            if kw.lower() in combined:
                return seg

    return None


# ============================================================
# 主采集流程
# ============================================================

def collect_reports(industry, segments, months, size, api_key, base_url, timeout, output_dir, force_iwencai_only=False):
    """主采集逻辑（双数据源版）。

    策略：
    - 有 IWENCAI_API_KEY 且有 report-search 可用 → 双源合并
    - 仅 IWENCAI_API_KEY 可用 → 仅用 iwencai
    - 仅东财可用 → 仅用东财
    - 都不可用 → 报错
    """
    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw" / "industry" / industry
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 全局时间过滤阈值：iwencai API 不按日期严格过滤，需要在客户端按 date 字段过滤
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
    print(f"[时间过滤] 仅保留 {cutoff_date_str} 之后的研报（{months} 个月窗口）")

    all_reports = {}  # dict {uid_or_key: report}
    sources_used = []
    source_stats = {}

    has_iwencai_key = bool(api_key)
    has_eastmoney = not force_iwencai_only and check_eastmoney_available()

    print(f"\n{'='*60}")
    print(f"[采集] 行业: {industry}")
    print(f"[采集] 环节: {segments}")
    print(f"[采集] 时间范围: {months} 个月 | 每环节: {size} 篇")
    print(f"[采集] iwencai API Key: {'✓ 已配置' if has_iwencai_key else '✗ 未配置'}")
    print(f"[采集] 东财 reportapi: {'✓ 可访问' if has_eastmoney else '✗ 不可访问或跳过'}")
    print(f"{'='*60}\n")

    if not has_iwencai_key and not has_eastmoney:
        print("[错误] 无可用的数据源！请配置 IWENCAI_API_KEY 或确保能访问东财 reportapi。")
        print(f"\n{MISSING_KEY_NOTICE}")
        sys.exit(2)

    failed_segments = []

    # ---------- 数据源 1: iwencai ----------
    if has_iwencai_key:
        print("--- [数据源: iwencai report-search] ---")
        iwencai_count = 0
        for seg in segments:
            query = f"{industry} {seg} 研报"
            print(f"[搜索] {query} ...", end=" ", flush=True)

            status, data = call_iwencai(query, size, api_key, base_url, timeout)

            if status == 401:
                print("FAIL (401 - API Key 无效)")
                failed_segments.append((seg, "iwencai_401"))
                continue
            elif status == 429:
                print("RATE LIMITED, 等待 3 秒后重试...")
                time.sleep(3)
                status, data = call_iwencai(query, size, api_key, base_url, timeout)

            if status != 200 or not data:
                print(f"FAIL (status={status})")
                failed_segments.append((seg, f"iwencai_{status}"))
                continue

            # 解析 iwencai 返回
            if isinstance(data, dict):
                if data.get("status_code") != 0:
                    print(f"API error: {data.get('message', '')}")
                    failed_segments.append((seg, f"iwencai_api_error:{data.get('message', '')}"))
                    continue
                items = data.get("data", [])
            elif isinstance(data, list):
                items = data
            else:
                items = []

            count = 0
            skipped_old = 0
            for item in items:
                report = parse_iwencai_report(item)
                if not report["uid"]:
                    report["uid"] = f"iw_{report['date']}_{report['title'][:40]}"

                # 严格时间过滤：iwencai API 不按日期严格过滤，返回结果可能包含早期研报
                if report["date"] and cutoff_date_str:
                    if report["date"] < cutoff_date_str:
                        skipped_old += 1
                        continue

                uid = report["uid"]
                if uid in all_reports:
                    continue
                report["matched_segment"] = seg
                all_reports[uid] = report
                count += 1
                iwencai_count += 1

            if skipped_old:
                print(f"{count} 篇（已过滤 {skipped_old} 篇早期研报）")
            else:
                print(f"{count} 篇")

        source_stats["iwencai"] = iwencai_count
        if iwencai_count > 0:
            sources_used.append("iwencai")
        print()

    # ---------- 数据源 2: 东财 reportapi ----------
    if has_eastmoney:
        print("--- [数据源: 东方财富 reportapi] ---")
        try:
            em_reports = call_eastmoney_industry_reports(
                industry=industry,
                months=months,
                page_size=100,
            )
            print(f"[东财] 获取到 {len(em_reports)} 篇行业研报（行业分类过滤 + segment 归类）")

            # 按环节归类
            em_count = 0
            for report in em_reports:
                # 匹配环节
                seg = match_segment(report, segments)
                if seg:
                    report["matched_segment"] = seg
                else:
                    # 无法匹配环节时标记为第一个环节
                    report["matched_segment"] = segments[0] if segments else "未分类"

                # 去重：与 iwencai 已有数据比较
                uid = report.get("uid", "")
                title_date_key = f"{report.get('date', '')}_{report.get('title', '')[:60]}"

                already_exists = False
                if uid and uid in all_reports:
                    already_exists = True
                if not already_exists:
                    for exist_r in all_reports.values():
                        exist_key = f"{exist_r.get('date', '')}_{exist_r.get('title', '')[:60]}"
                        if title_date_key and exist_key == title_date_key:
                            already_exists = True
                            break

                if not already_exists:
                    all_reports[uid or title_date_key] = report
                    em_count += 1

            source_stats["eastmoney"] = em_count
            if em_count > 0:
                sources_used.append("eastmoney")
            print(f"[东财] 去重后新增 {em_count} 篇")
        except Exception as exc:
            print(f"[东财] 采集异常: {exc}")

    # ---------- 数据源 3: fxbaogao.com ----------
    has_fxbaogao = check_fxbaogao_available()
    if has_fxbaogao:
        print("--- [数据源: 发现报告 fxbaogao.com] ---")
        try:
            # 行业级搜索 + 各环节搜索
            time_map = {1: "last1mon", 2: "last3mon", 3: "last3mon", 6: "last1year"}
            time_str = time_map.get(months, "last3mon")
            fx_queries = [industry] + segments
            fx_count = 0
            for q in fx_queries:
                fx_records = call_fxbaogao_reports(q, time_str=time_str, page_size=20)
                for rec in fx_records:
                    rec["matched_segment"] = match_segment(rec, segments) or segments[0] if segments else "未分类"
                    uid = rec.get("uid", "")
                    if uid and uid not in all_reports:
                        all_reports[uid] = rec
                        fx_count += 1
            source_stats["fxbaogao"] = fx_count
            if fx_count > 0:
                sources_used.append("fxbaogao")
            print(f"[fxbaogao] 去重后新增 {fx_count} 篇")
        except Exception as exc:
            print(f"[fxbaogao] 采集异常: {exc}")

        print()
    else:
        print("[fxbaogao] 不可用，跳过")
        print()

    # ---------- 数据源 4: hithink-industry-query（同花顺官方行业统计） ----------
    print("--- [数据源: 同花顺 hithink-industry-query] ---")
    industry_stats = fetch_industry_stats(industry, segments)
    if "error" not in industry_stats:
        stats_path = raw_dir / "industry_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(industry_stats, f, ensure_ascii=False, indent=2)
        print(f"[hithink] 行业统计数据已保存: {stats_path}")
        if industry_stats.get("valuation"):
            print(f"[hithink] 行业估值: {len(industry_stats['valuation'])} 条")
        if industry_stats.get("momentum"):
            print(f"[hithink] 板块行情: {len(industry_stats['momentum'])} 条")
        if industry_stats.get("seg_valuation"):
            for seg, data in industry_stats["seg_valuation"].items():
                print(f"[hithink] {seg} 环节数据: {len(data) if isinstance(data, list) else 'OK'}")
    else:
        print(f"[hithink] 跳过: {industry_stats['error']}")
    print()

    # ---------- 归类到环节 ----------
    categorized = {seg: [] for seg in segments}
    uncategorized = []

    for uid, report in all_reports.items():
        best_seg = match_segment(report, segments)
        if best_seg:
            categorized[best_seg].append(report)
        else:
            uncategorized.append(report)

    # 排序（按日期降序）
    for seg in segments:
        categorized[seg].sort(key=lambda r: r.get("date", "") or "", reverse=True)
    uncategorized.sort(key=lambda r: r.get("date", "") or "", reverse=True)

    all_list = sorted(all_reports.values(), key=lambda r: r.get("date", "") or "", reverse=True)

    # ---------- 输出文件 ----------
    index_data = {
        "industry": industry,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_range": f"{(datetime.now() - timedelta(days=months * 30)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}",
        "segments": segments,
        "total_reports": len(all_reports),
        "sources_used": sources_used,
        "source_stats": source_stats,
        "failed_segments": failed_segments,
        "reports": all_list,
    }

    index_path = raw_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"[输出] {index_path}")

    for seg in segments:
        seg_path = raw_dir / f"{seg}.json"
        seg_data = {
            "industry": industry,
            "segment": seg,
            "count": len(categorized[seg]),
            "reports": categorized[seg],
        }
        with open(seg_path, "w", encoding="utf-8") as f:
            json.dump(seg_data, f, ensure_ascii=False, indent=2)
        print(f"[输出] {seg_path} ({len(categorized[seg])} 篇)")

    if uncategorized:
        uncat_path = raw_dir / "uncategorized.json"
        with open(uncat_path, "w", encoding="utf-8") as f:
            json.dump({"count": len(uncategorized), "reports": uncategorized}, f, ensure_ascii=False, indent=2)
        print(f"[输出] {uncat_path} ({len(uncategorized)} 篇未归类)")

    print(f"\n[完成] 共采集 {len(all_reports)} 篇研报（去重后）")
    print(f"  数据源: {', '.join(sources_used) if sources_used else '无'}")
    if source_stats:
        for src, cnt in source_stats.items():
            print(f"    {src}: {cnt} 篇")
    print(f"  已归类: {sum(len(v) for v in categorized.values())} 篇")
    print(f"  未归类: {len(uncategorized)} 篇")
    print(f"  失败环节: {failed_segments}")


# ============================================================
# 公司模式采集
# ============================================================

def collect_company_reports(code, months, size, api_key, base_url, timeout, output_dir, force_iwencai_only=False):
    """公司模式采集：按股票代码拉取个股研报。"""
    code = str(code).zfill(6)
    output_dir = Path(output_dir)
    raw_dir = output_dir / "raw" / "company" / code
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 全局时间过滤阈值
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
    print(f"[时间过滤] 仅保留 {cutoff_date_str} 之后的研报（{months} 个月窗口）")

    all_reports = {}
    sources_used = []
    source_stats = {}

    has_iwencai_key = bool(api_key)
    has_eastmoney = not force_iwencai_only and check_eastmoney_available()

    print(f"\n{'='*60}")
    print(f"[公司采集] 代码: {code}")
    print(f"[公司采集] 时间范围: {months} 个月")
    print(f"[公司采集] iwencai API Key: {'✓ 已配置' if has_iwencai_key else '✗ 未配置'}")
    print(f"[公司采集] 东财 reportapi: {'✓ 可访问' if has_eastmoney else '✗ 不可访问或跳过'}")
    print(f"{'='*60}\n")

    if not has_iwencai_key and not has_eastmoney:
        print("[错误] 无可用的数据源！请配置 IWENCAI_API_KEY 或确保能访问东财 reportapi。")
        sys.exit(1)

    # --- 东财个股研报 (qType=0) ---
    if has_eastmoney:
        try:
            em_records = call_eastmoney_stock_reports(code, months)
            print(f"[东财] 获取 {len(em_records)} 篇个股研报")
            for rec in em_records:
                key = rec["uid"]
                if key not in all_reports:
                    all_reports[key] = rec
            sources_used.append("eastmoney")
            source_stats["eastmoney"] = len(em_records)
        except Exception as e:
            print(f"[东财] 获取个股研报失败: {e}")

    # --- iwencai 搜索 ---
    if has_iwencai_key:
        queries = [
            f"{code} 研报",
            f"{code} 深度分析 研报",
        ]
        iwencai_count = 0
        dedup_count = 0
        skipped_old = 0
        for q in queries:
            try:
                status, payload = call_iwencai(q, max(size, 20), api_key, base_url, timeout)
                if status != 200 or not payload:
                    print(f"[iwencai] 请求 '{q}' 返回状态 {status}")
                    continue
                items = payload.get("data", []) or []
                for raw in items:
                    rec = parse_iwencai_report(raw) if isinstance(raw, dict) else None
                    if not rec:
                        continue
                    # 严格时间过滤：iwencai API 不按日期过滤，需客户端按 date 字段过滤
                    if rec.get("date") and cutoff_date_str and rec["date"] < cutoff_date_str:
                        skipped_old += 1
                        continue
                    key = rec.get("uid", "")
                    if not key:
                        continue
                    if key not in all_reports:
                        all_reports[key] = rec
                        iwencai_count += 1
                    else:
                        dedup_count += 1
            except Exception as e:
                print(f"[iwencai] 搜索 '{q}' 失败: {e}")
                continue
            time.sleep(1)
        if skipped_old:
            print(f"[iwencai] 新增 {iwencai_count} 篇（已过滤 {skipped_old} 篇早期研报）")
        else:
            print(f"[iwencai] 新增 {iwencai_count} 篇（去重排除 {dedup_count} 篇）")

        if iwencai_count > 0:
            sources_used.append("iwencai")
            source_stats["iwencai"] = iwencai_count

        # --- 数据源 3: fxbaogao 公司搜索 ---
        if check_fxbaogao_available():
            try:
                time_map = {1: "last1mon", 2: "last3mon", 3: "last3mon", 6: "last1year"}
                time_str = time_map.get(months, "last3mon")
                fx_records = call_fxbaogao_reports(code, time_str=time_str, page_size=20)
                fx_count = 0
                for rec in fx_records:
                    uid = rec.get("uid", "")
                    if uid and uid not in all_reports:
                        all_reports[uid] = rec
                        fx_count += 1
                source_stats["fxbaogao"] = fx_count
                if fx_count > 0:
                    sources_used.append("fxbaogao")
                print(f"[fxbaogao] 去重后新增 {fx_count} 篇")
            except Exception as exc:
                print(f"[fxbaogao] 公司搜索失败: {exc}")

    # --- 输出 ---
    report_list = list(all_reports.values())
    report_list.sort(key=lambda x: x.get("date", ""), reverse=True)

    index_data = {
        "mode": "company",
        "code": code,
        "code_name": report_list[0].get("institution", "") if report_list else "",
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_range": f"{(datetime.now() - timedelta(days=months*30)).strftime('%Y-%m-%d')} ~ {datetime.now().strftime('%Y-%m-%d')}",
        "total_reports": len(report_list),
        "sources_used": sources_used,
        "source_stats": source_stats,
        "reports": report_list,
    }

    index_path = raw_dir / "reports.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"[输出] {index_path}")

    print(f"\n[完成] 共采集 {len(report_list)} 篇个股研报（去重后）")
    print(f"  数据源: {', '.join(sources_used) if sources_used else '无'}")
    if source_stats:
        for src, cnt in source_stats.items():
            print(f"    {src}: {cnt} 篇")


def main():
    parser = argparse.ArgumentParser(description="投资研究数据采集（双数据源·双模式）")
    parser.add_argument("--mode", default="industry", choices=["industry", "company"],
                        help="采集模式：industry=行业研报（默认）, company=个股研报")
    parser.add_argument("--industry", default=None, help="行业名（mode=industry 时必填）")
    parser.add_argument("--segments", default=None, help="产业环节列表，逗号分隔（mode=industry 时必填）")
    parser.add_argument("--code", default=None, help="股票代码，6位数字（mode=company 时必填）")
    parser.add_argument("--months", type=int, default=3, help="时间范围（月），默认 3")
    parser.add_argument("--size", type=int, default=10, help="每环节拉取篇数（仅 iwencai），默认 10")
    parser.add_argument("--base-url", default=os.getenv("IWENCAI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output-dir", default=None, help="输出根目录，默认为当前工作目录")
    parser.add_argument("--force-iwencai", action="store_true", default=False,
                        help="强制仅用 iwencai，不检测东财（降级模式）")
    args = parser.parse_args()

    api_key = os.getenv("IWENCAI_API_KEY")
    output_dir = args.output_dir or os.getcwd()

    if args.mode == "company":
        if not args.code:
            print("[错误] --mode company 需要 --code 参数", file=sys.stderr)
            sys.exit(1)
        collect_company_reports(
            code=args.code,
            months=args.months,
            size=args.size,
            api_key=api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            output_dir=output_dir,
            force_iwencai_only=args.force_iwencai,
        )
    else:
        if not args.industry or not args.segments:
            print("[错误] --mode industry 需要 --industry 和 --segments 参数", file=sys.stderr)
            sys.exit(1)
        segments = [s.strip() for s in args.segments.split(",") if s.strip()]
        if not segments:
            print("[错误] segments 不能为空", file=sys.stderr)
            sys.exit(1)
        collect_reports(
            industry=args.industry,
            segments=segments,
            months=args.months,
            size=args.size,
            api_key=api_key,
            base_url=args.base_url,
            timeout=args.timeout,
            output_dir=output_dir,
            force_iwencai_only=args.force_iwencai,
        )


if __name__ == "__main__":
    main()
