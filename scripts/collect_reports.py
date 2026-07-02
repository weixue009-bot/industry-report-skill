#!/usr/bin/env python3
"""产业研究报告数据采集脚本（双数据源版）。
支持：
1. iwencai report-search（需 IWENCAI_API_KEY）
2. 东方财富 reportapi（免费公开接口，无需 Key）

当两个源都可用时，合并去重后输出；只有一个可用时，降级使用单源；都不可用时报错。
"""

import argparse
import json
import os
import random
import secrets
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


def call_eastmoney_industry_reports(industry_keywords, months, page_size=50):
    """调用东财 reportapi 获取行业研报（qType=1）。
    
    Args:
        industry_keywords: 行业相关关键词列表，用于搜索匹配
        months: 时间范围（月）
        page_size: 每页条数，最大100
    
    Returns:
        解析后的研报列表（统一格式）
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months * 30)
    begin = start_date.strftime("%Y-%m-%d")

    all_records = []
    max_pages = 3  # 东财每页最多100条，3页足够覆盖近期研报

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

            # 处理每条记录
            for item in rows:
                # 标题关键词匹配过滤：只保留与行业关键词相关的研报
                title = item.get("title", "") or ""
                title_lower = title.lower()
                # 如果有关键词且标题不匹配，跳过
                if industry_keywords and not any(
                    kw.lower() in title_lower for kw in industry_keywords
                ):
                    continue

                # 构建统一格式
                pub_time = item.get("publishDate", "")
                if isinstance(pub_time, str):
                    pub_time = pub_time[:10]

                record = {
                    "uid": f"em_{item.get('infoCode', '')}",
                    "title": title.strip(),
                    "summary": "",
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
                    "institution": (item.get("orgSName") or "").strip(),
                    "analyst": "",
                    "date": pub_time,
                    "url": "",
                    "rating": (item.get("emRatingName") or "").strip(),
                    "source": "eastmoney",
                    "info_code": item.get("infoCode", ""),
                    "industry_name": item.get("indvInduName", ""),
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

    return {
        "uid": uid,
        "title": str(title).strip(),
        "summary": str(summary).strip(),
        "institution": str(institution).strip(),
        "analyst": str(analyst).strip(),
        "date": str(publish_time).strip(),
        "url": str(url).strip(),
        "rating": str(rating).strip(),
        "source": "iwencai",
    }


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
    """根据标题关键词匹配产业环节。返回匹配的环节名，无匹配返回 None。"""
    title_lower = report["title"].lower()
    summary_lower = report["summary"].lower()

    for seg in segments:
        seg_lower = seg.lower()
        if seg_lower in title_lower or seg_lower in summary_lower:
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
    raw_dir = output_dir / "raw" / industry
    raw_dir.mkdir(parents=True, exist_ok=True)

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
            for item in items:
                report = parse_iwencai_report(item)
                if not report["uid"]:
                    report["uid"] = f"iw_{report['date']}_{report['title'][:40]}"

                uid = report["uid"]
                if uid in all_reports:
                    continue
                report["matched_segment"] = seg
                all_reports[uid] = report
                count += 1
                iwencai_count += 1

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
                industry_keywords=[industry] + segments,
                months=months,
                page_size=50,
            )
            print(f"[东财] 获取到 {len(em_reports)} 篇行业研报（关键词过滤后）")

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


def main():
    parser = argparse.ArgumentParser(description="产业研究报告数据采集（双数据源版）")
    parser.add_argument("--industry", required=True, help="行业名")
    parser.add_argument("--segments", required=True, help="产业环节列表，逗号分隔")
    parser.add_argument("--months", type=int, default=3, help="时间范围（月），默认 3")
    parser.add_argument("--size", type=int, default=10, help="每环节拉取篇数（仅 iwencai），默认 10")
    parser.add_argument("--base-url", default=os.getenv("IWENCAI_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--output-dir", default=None, help="输出目录，默认为当前工作目录")
    parser.add_argument("--force-iwencai", action="store_true", default=False,
                        help="强制仅用 iwencai，不检测东财（降级模式）")
    args = parser.parse_args()

    api_key = os.getenv("IWENCAI_API_KEY")
    segments = [s.strip() for s in args.segments.split(",") if s.strip()]
    if not segments:
        print("[错误] segments 不能为空", file=sys.stderr)
        sys.exit(1)

    output_dir = args.output_dir or os.getcwd()

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
