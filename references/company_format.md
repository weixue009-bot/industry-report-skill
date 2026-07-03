# 公司分析字段写作规范（v2.2 精简版）

## 数据模型概览

公司分析 `analysis.json` 采用精简的卡片式结构，只保留关键判断字段：

```json
{
  "mode": "company",
  "code": "600360",
  "company_name": "华微电子",
  "fetch_time": "2026-07-04",
  "time_range": "2026-04 ~ 2026-07",
  "source_report_count": 0,
  "sources_used": ["iwencai"],
  "source_stats": {"iwencai": 0, "eastmoney": 0},
  "company_identity": { ... },
  "one_sentence_view": "...",
  "chain_positioning": "...",
  "key_theme_relation": { ... },
  "growth_drivers": [...],
  "business_breakdown": { ... },
  "competitive_comparison": { ... },
  "profit_logic": [...],
  "real_bottlenecks": [...],
  "key_metrics": [...],
  "research_path": "...",
  "financial_snapshot": { ... },
  "risks": [...],
  "evidence_sources": [...]
}
```

---

## company_identity — 公司身份

| 字段 | 说明 |
|------|------|
| `code` | 股票代码 |
| `name` | 公司简称 |
| `industry` | 所属行业 |
| `market_cap` | 总市值（格式化后的字符串，如"143.66亿"） |
| `price` | 当前股价 |
| `pe_ttm` | PE(TTM) |
| `pb` | PB |
| `main_business` | 一句话主营业务 |

---

## one_sentence_view — 一句话看懂

- 用"不是...而是..."句式点出核心定位
- 普通人 5 秒内能看懂
- 说明真正的研究逻辑是什么

示例：
> 华微电子不是AI概念股，而是新能源车和光伏储能需求驱动下的国产功率半导体IDM；它的研究逻辑不是'能不能蹭热点'，而是'国产替代和终端需求能否真正拉动它的IGBT/MOSFET放量，并改善毛利率'。

---

## chain_positioning — 产业链定位

- 公司在产业链中的位置（上游/中游/下游）
- 核心客户是谁
- 200-300 字，避免冗长

---

## key_theme_relation — 核心概念关系

```json
{
  "theme": "新能源 + 国产替代",
  "summary": "一句话说明公司与核心概念的真实关系（不是蹭热点）",
  "points": ["要点1", "要点2", "要点3"]
}
```

---

## growth_drivers — 增量驱动

```json
[
  {"driver": "驱动因素", "impact": "高/中/低", "note": "一句话解释"}
]
```

最多 3-4 条，按影响优先级排序。

---

## business_breakdown — 业务拆分

```json
{
  "description": "业务拆分说明",
  "segments": [
    {"name": "业务线", "share": "占比", "note": "说明"}
  ]
}
```

2-4 个业务线即可，不用过细。

---

## competitive_comparison — 竞争对比

```json
{
  "global": "一句话说明全球格局",
  "china": [
    {"name": "公司名", "position": "一句话定位", "vs": "与目标公司的对比"}
  ]
}
```

国内对比 2-3 家即可。

---

## profit_logic — 盈利逻辑

2-4 条，用动词开头，说明公司怎么赚钱、利润驱动是什么。

---

## real_bottlenecks — 真正的卡点

```json
[
  {"bottleneck": "卡点名称", "detail": "具体说明"}
]
```

2-4 条，必须具体可验证，不泛泛而谈。

---

## key_metrics — 关键跟踪指标

```json
[
  {"metric": "指标名", "target": "目标", "why": "为什么关注"}
]
```

3-5 个指标，目标值明确。

---

## research_path — 一句话研究路径

- 给出一条可执行的研究路线
- 用箭头 → 连接
- 示例：先确认行业周期 → 再跟踪产品出货 → 最后验证毛利率

---

## financial_snapshot — 财务快照

只保留最关键的 6-8 个指标：

```json
{
  "report_date": "2026Q1",
  "revenue": 6.66,
  "revenue_unit": "亿",
  "revenue_yoy": 3.61,
  "parent_netprofit": 0.58,
  "profit_unit": "亿",
  "profit_yoy": 5.44,
  "gross_margin": 21.15,
  "net_margin": 8.99,
  "roe": 1.66,
  "debt_ratio": 34.04,
  "basic_eps": 0.06
}
```

---

## risks — 风险与反证

2-5 条，每条具体可验证。

---

## evidence_sources — 证据来源

```json
[
  {"level": "A", "content": "...", "source": "年报/公告"},
  {"level": "B", "content": "...", "source": "券商研报"},
  {"level": "C", "content": "...", "source": "线索待验证"}
]
```

等级：A（一手）/ B（研报）/ C（线索）。

---

## 已弃用字段

以下字段在 v2.2 模板中不再渲染：

- `reports`（机构研报矩阵）
- `eps_forecast`（EPS 预测与一致性预期）
- `moat`（护城河）
- `growth_mechanism`（增长机制，被 growth_drivers 替代）
- `valuation`（完整估值对象，被 company_identity 中的关键字段替代）

如需保留研报数据，可继续写入 `reports` 字段，但模板不会展示。

---

## 反模式

- 不要从泛泛的 SWOT 开始
- 不要堆数据，只保留改变判断的关键字段
- 不要在没有来源时称"龙头""领先"
- 不要省略反证条件和风险
