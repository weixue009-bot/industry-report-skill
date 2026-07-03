#!/usr/bin/env python3
"""产业研究报告 HTML 生成脚本。
读取 analysis JSON → 注入到 HTML 模板 → 输出自包含 HTML 文件。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def load_template(template_path=None):
    """加载 HTML 模板。"""
    if template_path:
        path = Path(template_path)
    else:
        # 默认模板路径：与脚本同级的 templates/report.html
        path = Path(__file__).resolve().parent.parent / "templates" / "report.html"

    if not path.exists():
        print(f"[错误] 模板文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_analysis(data_path):
    """加载分析数据 JSON。"""
    path = Path(data_path)
    if not path.exists():
        print(f"[错误] 分析数据文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_data_source(industry, analysis):
    """根据实际使用的数据源动态生成数据来源说明。
    优先从 analysis JSON 中的 sources_used / source_stats 读取，
    若没有则回退到 index.json，都没有则使用默认文本。
    """
    sources_used = analysis.get("sources_used", [])
    source_stats = analysis.get("source_stats", {})

    # 如果 analysis 中没有，尝试从 index.json 读取
    if not sources_used:
        index_path = Path("raw") / industry / "index.json"
        if index_path.exists():
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    idx = json.load(f)
                sources_used = idx.get("sources_used", [])
                source_stats = idx.get("source_stats", {})
            except Exception:
                pass

    if not sources_used:
        return "数据来源：研究报告数据库"

    labels = {
        "iwencai": "同花顺i问财",
        "eastmoney": "东方财富",
    }
    parts = ["数据来源："]
    source_names = []
    for s in sources_used:
        label = labels.get(s, s)
        count = source_stats.get(s, 0)
        if count:
            source_names.append(f"{label}（{count}篇）")
        else:
            source_names.append(label)
    parts.append(" + ".join(source_names))
    return "".join(parts)


def build_html(template, analysis):
    """将分析数据注入模板，生成完整 HTML。"""
    industry = analysis.get("industry", "未知行业")
    fetch_time = analysis.get("fetch_time", datetime.now().strftime("%Y-%m-%d"))
    time_range = analysis.get("time_range", "未知")
    report_count = analysis.get("source_report_count", 0)
    data_source = build_data_source(industry, analysis)

    # 序列化 JSON 用于嵌入
    data_json = json.dumps(analysis, ensure_ascii=False, indent=2)

    html = template
    html = html.replace("{{INDUSTRY}}", industry)
    html = html.replace("{{GEN_TIME}}", fetch_time)
    html = html.replace("{{REPORT_COUNT}}", str(report_count))
    html = html.replace("{{TIME_RANGE}}", time_range)
    html = html.replace("{{DATA_SOURCE}}", data_source)
    html = html.replace("{{DATA_JSON}}", data_json)

    # 验证所有占位符都已替换
    remaining = [line for line in html.split("\n") if "{{" in line and "}}" in line]
    if remaining:
        print(f"[警告] 存在未替换的占位符:")
        for line in remaining:
            print(f"  {line.strip()}")

    return html


def save_report(html, output_path):
    """保存最终 HTML 文件。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[输出] {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="产业研究报告 HTML 生成")
    parser.add_argument("--data", required=True, help="分析数据 JSON 文件路径")
    parser.add_argument("--template", default=None, help="HTML 模板路径，默认使用内置模板")
    parser.add_argument("--output", required=True, help="输出 HTML 文件路径")
    args = parser.parse_args()

    # 加载模板和分析数据
    template = load_template(args.template)
    analysis = load_analysis(args.data)

    # 生成 HTML
    html = build_html(template, analysis)

    # 保存
    output_path = save_report(html, args.output)
    print(f"[完成] 报告已生成: {output_path}")
    print(f"  文件大小: {output_path.stat().st_size:,} 字节")
    print(f"  直接用浏览器打开即可查看")


if __name__ == "__main__":
    main()
