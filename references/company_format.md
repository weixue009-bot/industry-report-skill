# 公司分析字段写作规范（v2.3 模板驱动版）

## 核心原则

**模板驱动数据**。`company_report.html` 的 JS 渲染逻辑定义了 18 个顶层字段的精确结构。Step B3 写 `analysis.json` 时，必须严格按照以下清单逐一填写——字段名、数据类型、嵌套结构任何一个不匹配，都会导致对应卡片显示"待补充"或渲染异常。

---

## 公司 analysis.json 全字段清单

模板 `company_report.html` 第 274-398 行定义 18 个顶层字段的渲染顺序。以下按模板读取顺序排列：

| 序号 | 卡片 | 顶层字段 | 模板行 | 数据类型 | 必填 | 常见错误 |
|:--:|------|---------|:-----:|:--------:|:--:|---------|
| 1 | header | `company_name` | 280 | string | ✅ | 缺字段 |
| 2 | header | `fetch_time` | 284 | string | ✅ | 缺字段 |
| 3 | 一句话看懂 | `one_sentence_view` | 288 | string | ✅ | 缺字段 |
| 4 | 公司身份 | `company_identity` | 275 | **对象** | ✅ | 缺字段/结构错 |
| 5 | 产业链 | `chain_positioning` | 305 | **string** (文本) | ✅ | 缺字段 |
| 6 | 产业链流程 | `chain_flow` | 307 | **数组** `[{title,desc,highlight?}]` | ✅ | 写成对象而非数组 |
| 7 | 核心概念关系 | `key_theme_relation` | 317 | **对象** `{theme,summary,points[]}` | ✅ | 缺 `summary` |
| 8 | 增量驱动 | `growth_drivers` | 326 | **数组** `[{driver,impact,note}]` | ✅ | 缺字段 |
| 9 | 业务拆分 | `business_breakdown` | 334 | **对象** `{description,segments:[{name,share,note}]}` | ✅ | 写成裸数组 |
| 10 | 竞争对比 | `competitive_comparison` | 342 | **对象** `{position_summary,global_companies[],china_companies[]}` | ✅ | 缺 `position_summary` |
| 11 | 盈利逻辑 | `profit_logic` | 368 | **数组** `[string]` | ✅ | 缺字段 |
| 12 | 证据来源 | `evidence_sources` | 374 | **数组** `[{level,content,source}]` | ✅ | 缺字段 |
| 13 | 真正的卡点 | `real_bottlenecks` | 381 | **数组** `[{bottleneck,detail}]` | ✅ | 写成字符串数组 |
| 14 | 关键跟踪指标 | `key_metrics` | 388 | **数组** `[{metric,target,why}]` | ✅ | 缺字段 |
| 15 | 研究路径 | `research_path` | 394 | string | ✅ | 缺字段 |
| 16 | 风险反证 | `risks` | 397 | **数组** `[string]` | ✅ | 缺字段 |
| 17 | meta | `code` | 282 | string | ✅ | — |
| 18 | meta | `company_identity.main_business` | 281 | string | ✅ | 缺字段 |

### 字段格式规则（上海机电修复经验总结）

```json
{
  // ⚠️ company_identity 必须有 market_cap（字符串+亿单位），模板读 ci.market_cap
  "company_identity": {
    "market_cap": "176.06亿",        // 字符串！模板不读 market_cap_yi
    "price": 21.83,
    "pe_ttm": 28.65,
    "pb": 1.57,
    "main_business": "电梯、机电装备"
  },

  // ⚠️ chain_flow 必须是数组，不是对象！
  // 第 307 行检查：d.chain_flow && d.chain_flow.length
  // 对象没有 .length 属性 → 条件为 false → 走 fallback
  "chain_flow": [
    {"title": "上游", "desc": "原材料", "highlight": false},
    {"title": "中游 · 公司", "desc": "核心业务", "highlight": true},
    {"title": "下游", "desc": "终端客户"}
  ],

  // ⚠️ key_theme_relation 必须有 summary（string），否则显示"待补充"
  // 模板第 319 行：kt.summary || '待补充'
  "key_theme_relation": {
    "theme": "核心概念",
    "summary": "一句话说明公司与核心概念的真实关系",
    "points": ["要点1", "要点2"]
  },

  // ⚠️ business_breakdown 必须是对象，嵌套 segments 数组
  // 模板第 334 行：var bb = d.business_breakdown || {}; bb.segments
  // 裸数组会令 bb.segments 为 undefined → 不渲染
  "business_breakdown": {
    "description": "业务拆分说明",
    "segments": [
      {"name": "业务线", "share": "~X%", "note": "说明"}
    ]
  },

  // ⚠️ real_bottlenecks 必须是对象数组 [{bottleneck, detail}]
  // 模板第 382-383 行遍历 b.bottleneck / b.detail
  // 字符串数组会渲染 undefined → 卡片内空
  "real_bottlenecks": [
    {"bottleneck": "卡点名称", "detail": "具体说明"}
  ],

  // ✅ 以下 4 个字段是简单的数组或字符串，出错概率低
  // growth_drivers: [{driver, impact, note}] — 数组对象
  // profit_logic: [string] — 字符串数组
  // evidence_sources: [{level, content, source}] — 对象数组
  // key_metrics: [{metric, target, why}] — 对象数组
}
```

---

## 各字段详细写作规范

### company_identity — 公司身份

```json
{
  "code": "600835",
  "name": "上海机电",
  "industry": "机械设备 — 专用设备 — 楼宇设备",
  "market_cap": "176.06亿",       // ⚠️ 字符串，含"亿"单位，模板读 ci.market_cap
  "price": 21.83,
  "pe_ttm": 28.65,
  "pb": 1.57,
  "change_pct": 5.26,
  "listing_date": "1994-02-24",
  "main_business": "电梯、印刷包装机械、液压机械"
}
```

- `market_cap` 必须是字符串格式（如"143.66亿"），模板第 294 行用 `String(it.value)` 渲染

### one_sentence_view — 一句话看懂

- 用"X 是什么角色，关键看什么"句式
- 不再使用"不是...而是..."（已废弃，改后更自然）
- 普通人 5 秒内能看懂核心研究逻辑

### chain_positioning + chain_flow — 产业链

- `chain_positioning`：文本描述（200-300字），模板读 `d.chain_positioning` 纯文本
- `chain_flow`：**必须是数组** `[{title,desc,highlight?}]`，不是对象——模板第 307 行检查 `.length`
- `chain_flow` 格式：上游(1个) → 中游·公司名(highlight=true) → 下游(1个)

### key_theme_relation — 核心概念关系

```json
{
  "theme": "概念名",
  "summary": "一句话说明公司与概念的真实关系，不是蹭热点",  // 必填！
  "points": ["要点1", "要点2", "要点3"]
}
```

- `summary` 是**必填字段**（模板第 319 行 `kt.summary || '待补充'`）

### business_breakdown — 业务拆分

```json
{
  "description": "一句话总结公司业务结构",
  "segments": [
    {"name": "业务线名", "share": "~X%", "note": "该业务的核心说明"}
  ]
}
```

- **必须是对象**（含 `description` + `segments` 数组），不是裸数组

### competitive_comparison — 竞争对比

```json
{
  "position_summary": "一句话说明该公司的市场定位",
  "global_companies": [
    {"name": "对标公司", "tag": "全球", "position": "定位", "vs": "与目标公司的差距"}
  ],
  "china_companies": [
    {"name": "对标公司", "tag": "国内", "position": "定位", "vs": "与目标公司的差距"}
  ]
}
```

- `position_summary` 是**必填字段**（模板第 345 行 `'待补充'`）
- `global_companies` / `china_companies` 非必填，但建议至少写 2-3 家国内对比

### real_bottlenecks — 真正的卡点

- **必须是对象数组** `[{bottleneck, detail}]`，不是字符串数组
- 模板第 382-383 行遍历 `b.bottleneck` 和 `b.detail`——字符串数组这两个属性都是 undefined

### profit_logic — 盈利逻辑

- 简单字符串数组 `["驱动1", "驱动2", "驱动3"]`
- 用动词开头，3-4 条

### evidence_sources — 证据来源

```json
[
  {"level": "A", "content": "描述", "source": "来源"},
  {"level": "B", "content": "描述", "source": "券商研报 2026-06-01"}
]
```

- `level` 取值：A（一手）/ B（研报）/ C（线索）

### key_metrics — 关键跟踪指标

```json
[
  {"metric": "指标名", "target": "目标值/状态", "why": "为什么关注"}
]
```

---

## 公司 analysis.json 完整模板

> 写 analysis.json 时，逐字段对照以下模板，缺任何字段都会导致对应卡片显示"待补充"。

```json
{
  "mode": "company",
  "code": "600000",
  "company_name": "公司简称",
  "fetch_time": "2026-07-04",
  "time_range": "2026-04 ~ 2026-07",
  "source_report_count": 20,
  "sources_used": ["fxbaogao"],
  "source_stats": {"fxbaogao": 20},

  "company_identity": {
    "code": "600000",
    "name": "公司简称",
    "industry": "行业分类",
    "market_cap": "XXX亿",                         // string！
    "price": 21.83,
    "pe_ttm": 28.65,
    "pb": 1.57,
    "change_pct": 5.26,
    "listing_date": "YYYY-MM-DD",
    "main_business": "主营业务一句话"
  },

  "one_sentence_view": "一句话核心研究逻辑",

  "chain_positioning": "公司产业链定位文本描述（200-300字）",

  "chain_flow": [                                    // 数组，不是对象！
    {"title": "上游", "desc": "原材料"},
    {"title": "中游 · 公司简称", "desc": "核心业务", "highlight": true},
    {"title": "下游", "desc": "终端客户"}
  ],

  "key_theme_relation": {
    "theme": "核心概念",
    "summary": "一句话说明关系",                       // 必填！
    "points": ["要点1", "要点2"]
  },

  "growth_drivers": [
    {"driver": "驱动1", "impact": "高", "note": "说明"}
  ],

  "business_breakdown": {                            // 对象，不是数组！
    "description": "业务结构说明",
    "segments": [
      {"name": "业务线", "share": "~X%", "note": "说明"}
    ]
  },

  "competitive_comparison": {
    "position_summary": "市场定位",
    "global_companies": [
      {"name": "对标", "tag": "全球", "position": "定位", "vs": "差距"}
    ],
    "china_companies": [
      {"name": "对标", "tag": "国内", "position": "定位", "vs": "差距"}
    ]
  },

  "profit_logic": [
    "动词开头的盈利逻辑1",
    "动词开头的盈利逻辑2"
  ],

  "evidence_sources": [
    {"level": "A", "content": "内容", "source": "来源"}
  ],

  "real_bottlenecks": [                              // 对象数组，不是字符串数组！
    {"bottleneck": "卡点名称", "detail": "具体说明"}
  ],

  "key_metrics": [
    {"metric": "指标", "target": "目标", "why": "为什么关注"}
  ],

  "research_path": "一句话研究路径",

  "risks": [
    "具体风险描述"
  ]
}
```

## 常见错误清单

| # | 错误 | 表现 | 根因 | 需要修正的格式 |
|---|------|------|------|--------------|
| 1 | `company_identity` 缺 `market_cap` | 身份卡片"总市值: N/A" | 腾讯财经返回 `market_cap_yi` 而非 `market_cap` | 新增 `"market_cap": "XXX亿"` |
| 2 | `chain_flow` 写了对象而非数组 | 产业链流程显示"待补充" | 模板第 307 行检查 `.length`，对象无此属性 | 改为 `[{title,desc,highlight?}]` 数组 |
| 3 | `key_theme_relation` 缺 `summary` | 核心概念关系显示"待补充" | 模板第 319 行 `kt.summary \|\| '待补充'` | 新增 `"summary"` 字符串字段 |
| 4 | `business_breakdown` 写了裸数组 | 业务拆分卡片空 | 模板第 334 行读 `bb.segments`，数组无此属性 | 改为 `{description, segments:[]}` 对象 |
| 5 | `real_bottlenecks` 写了字符串数组 | 卡点卡片空 | 模板第 382 行读 `b.bottleneck`，字符串为 undefined | 改为 `[{bottleneck, detail}]` 对象数组 |
| 6 | 竞争对比缺 `position_summary` | 定位行显示"待补充" | 模板第 345 行 | 新增 `"position_summary"` |
| 7 | `chain_positioning` 缺字段 | 产业链文本显示"待补充" | 模板第 305 行 | 新增链定位文本 |
| 8 | 忘记 `market_cap` 用 string 格式 | 市值显示 [object Object] | 模板用 `String(it.value)` 渲染 | 写为字符串 `"XXX亿"` |

---

## 初次写 analysis.json 的检查清单

写完后逐一确认以下 18 个条目：

- [ ] `company_name` — 公司名存在
- [ ] `fetch_time` — 存在
- [ ] `one_sentence_view` — 并非"不是A而是B"句式
- [ ] `company_identity.market_cap` — 字符串格式 `"XXX亿"`，非数字
- [ ] `company_identity.price/pe_ttm/pb` — 数字
- [ ] `chain_positioning` — 文本(200-300字)
- [ ] `chain_flow` — **数组** `[{title,desc,highlight?}]`，非对象
- [ ] `key_theme_relation.summary` — 字符串，非空
- [ ] `key_theme_relation.points` — 数组，非空
- [ ] `growth_drivers` — 数组，每条含 `driver/impact/note`
- [ ] `business_breakdown` — **对象** `{description, segments:[]}`，非裸数组
- [ ] `competitive_comparison.position_summary` — 字符串
- [ ] `profit_logic` — 字符串数组，3-4 条
- [ ] `evidence_sources` — 对象数组，每条含 `level/content/source`
- [ ] `real_bottlenecks` — **对象数组** `[{bottleneck, detail}]`，非字符串数组
- [ ] `key_metrics` — 对象数组，每条含 `metric/target/why`
- [ ] `research_path` — 字符串
- [ ] `risks` — 字符串数组，2-5 条
