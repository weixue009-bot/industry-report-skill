---
name: industry-report
description: "AI 驱动产业研究报告生成器。从同花顺 iwencai + 东方财富 reportapi 双数据源拉取研报，AI 分析后生成单文件自包含 HTML 报告。用户只需说出行业名称即可。"
user-invocable: true
metadata:
  emoji: "🏭"
  skillKey: "industry-report"
  requires:
    env: ["IWENCAI_API_KEY"]
  primaryEnv: "IWENCAI_API_KEY"
  triggers: ["产业研究报告", "行业研报分析", "生成XX行业报告", "产业分析报告", "产业链研究"]
---

# 产业研究报告 Skill

## 定位

用户只需说出"查 XX 行业"，剩余全自动：
1. AI 先拉取行业研报，从研报标题和内容中**自动发现**产业链细分环节
2. 用户确认环节后，按环节采集研报
3. AI 读取研报、提取各环节分析
4. 生成单文件 HTML 报告（浏览器直接打开）

---

## 两种输入模式

### 模式 A：用户只给行业名（推荐）

用户：`查 人形机器人 产业研究报告`

Agent 自动发现环节。

### 模式 B：用户给行业 + 环节

用户：`查 人形机器人，环节：谐波减速器、行星滚柱丝杠、无框力矩电机`

跳过环节发现步骤，直接进入数据采集。

---

## 完整工作流（5 步）

### Step 1: 解析输入

从用户消息中提取：

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `industry` | 行业名称 | 必填 |
| `segments` | 环节列表（可选） | 空 = AI 自动发现 |
| `months` | 时间范围 | 3 个月 |
| `size` | 每环节拉取篇数 | 10 |

---

### Step 2: 环节发现（仅模式 A，无 segments 时执行）

#### 2.1 拉取行业全景研报

用 `report-search` skill 做一次宽泛搜索，或直接调用 API：

查询示例：`{行业名} 产业链 行业深度 研报`

**按用户指定的时间范围尽量全面拉取**（默认 3 个月）。不需要分类——目的是看标题和摘要来发现环节。如果按时间范围拉取到太多结果（超过 50 篇），取前 50 篇即可，已足够识别高频关键词和产业链结构。

#### 2.2 AI 分析发现环节

Agent 读取研报标题和摘要，自动识别产业链环节。原则：

1. **高频关键词**：研报标题中反复出现的细分产品名/技术名/零部件名
2. **产业链位置**：每个环节在产业链中的位置（上游材料/中游零部件/下游应用）
3. **合并同类项**：意义相近的关键词合并，如"关节电机""力矩电机""伺服电机"→ 合并为"电机"
4. **数量控制**：至少 3 个、最多 8 个环节

**用户不需要确认，发现后直接进入 Step 3 数据采集。**

---

### Step 3: 数据采集

按确认后的环节列表运行采集脚本：

```bash
python C:\Users\001\.workbuddy\skills\industry-report\scripts\collect_reports.py \
  --industry "{行业名}" \
  --segments "{环节1,环节2,环节3}" \
  --months {月数} \
  --size {每环节篇数}
```

脚本输出到 `raw/{行业}/` 目录：
- `index.json`：全部研报索引（日期、机构、标题、环节分类、URL、摘要）
- `{环节名}.json`：该环节专属研报列表

**双数据源架构**：
采集脚本为**双源平级架构**：两个数据源都是主力数据源，只要有可用就同时采集、合并去重：

| 数据源 | 认证 | 覆盖情况 | 特点 |
|--------|------|----------|------|
| **iwencai report-search** | 需 `IWENCAI_API_KEY` | 按环节关键词精准搜索 | 匹配准、带摘要 |
| **东方财富 reportapi** | 免费公开，无需 Key | 按行业关键词过滤行业研报 | 覆盖广、免费 |

- **两个都可用** → 同时从两个源拉取，**自动合并去重**（按 uid + title+date 联合去重，避免同一篇研报重复计数）
- **仅一个可用** → 自动使用可用源，不影响采集
- **都不可用** → 报错提示

**API 配置**：
- iwencai：从环境变量 `IWENCAI_API_KEY` 读取 Key（由 skill 系统自动注入）
- 东财：无需配置，脚本自动检测网络可达性

---

### Step 4: AI 分析（Agent 主导执行）

Agent 需要完成两个层次的分析：**总览分析** 和 **环节分析**。

#### 4.1 先读研报（三层读取策略）

对每个环节，按以下优先级读取研报内容：

| 层级 | 读取方式 | 内容长度 | 覆盖范围 |
|------|----------|---------|----------|
| **第1层** | `WebFetch` 打开最新 3 篇 iwencai 来源研报的 URL | 全文 | 每环节最新 3 篇 |
| **第2层** | 使用 record 的 `content` 字段（对应 iwencai 的 `source_original`） | 500-2000 字正文节选 | 所有 iwencai 来源研报 |
| **第3层** | 使用 record 的 `summary` 字段（API 摘要） | 200-300 字 | 所有研报 |

执行逻辑：

1. **每环节优先抓最新 3 篇有 URL 的研报全文**（WebFetch 10JQKA 报告页面）
2. **URL 不可访问或内容不足时**，fallback 到 `content` 正文节选
3. **最后一层 fallback**：仅当上述两层都不可用时，用 `summary` 摘要
4. 分析时优先引用第1层全文内容，其次第2层正文节选，再次第3层摘要

#### 4.2 输出分析 JSON

按以下结构生成 `analysis/{行业}/analysis.json`：

```json
{
  "industry": "行业名",
  "fetch_time": "2026-07-02",
  "time_range": "2026-04 ~ 2026-07",
  "source_report_count": 47,
  "sources_used": ["iwencai", "eastmoney"],
  "source_stats": {"iwencai": 44, "eastmoney": 3},
  "overview": {
    "judgment": "一句话核心判断：用普通人能理解的语言，5秒内抓住该行业最关键的投资判断",
    "proposition": "一句话命题：用'不是X，而是Y'句式点出市场认知偏差。如'CPO不是光模块换个名字，而是AI集群网络的功耗与带宽问题的解'",
    "definition": "行业定义：用1-2句话说明这个行业是什么、做什么、为什么有经济意义",
    "concept_clarification": [
      {"dimension": "维度名（如可插拔光模块）", "points": ["一句话要点1", "一句话要点2", "一句话要点3"]},
      {"dimension": "维度名（如LPO）", "points": ["一句话要点1", "一句话要点2", "一句话要点3"]},
      {"dimension": "维度名（如CPO）", "points": ["一句话要点1", "一句话要点2", "一句话要点3"]}
    ],
    "supply_chain": {
      "demand": ["需求端1", "需求端2"],
      "core_segments": ["环节A（占比%）", "环节B（占比%）"],
      "upstream": ["上游材料1", "上游设备2"]
    },
    "sector_scores": {
      "section_name": "板块评分总览",
      "dimensions": [
        {"name": "产业确定性", "score": 85, "note": "说明"},
        {"name": "爆发弹性", "score": 90, "note": "说明"},
        {"name": "估值位置", "score": 65, "note": "说明"},
        {"name": "资金动向", "score": 72, "note": "说明"},
        {"name": "催化剂密度", "score": 60, "note": "说明"},
        {"name": "周期错位", "score": 55, "note": "说明"},
        {"name": "板块综合评分", "score": 75, "note": "说明"}
      ]
    },
    "core_stock_pool": {
      "groups": [
        {
          "category": "分组名（如系统/芯片）",
          "role_desc": "该组的一句话定位（如'芯片架构的中枢'）",
          "stocks": [
            {"name": "公司名", "code": "300001", "role": "领先者", "segment": "所属环节", "logic": "入选逻辑一句话"}
          ]
        }
      ]
    },
    "cost_breakdown": [
      {"component": "环节名", "ratio": 35, "note": "占比说明"}
    ],
    "production_timeline": [
      {"year": "2024", "event": "里程碑事件"},
      {"year": "2025", "event": "里程碑事件"}
    ],
    "key_constraints": [
      {"id": 1, "label": "约束名称", "detail": "该约束的具体说明：为什么卡脖子、稀缺性来源"},
      {"id": 2, "label": "约束名称", "detail": "说明"},
      {"id": 3, "label": "约束名称", "detail": "说明"}
    ],
    "profit_logic": [
      "动词开头的盈利逻辑短句1（如'降传输功耗'）",
      "动词开头的盈利逻辑短句2（如'提高端口密度'）",
      "动词开头的盈利逻辑短句3（如'绑定客户架构'）"
    ],
    "segment_priority": [
      {"rank": 1, "segment": "环节名", "reason": "为什么这个环节最值得优先研究：稀缺性最强/确定性最高/时间窗口最近"},
      {"rank": 2, "segment": "环节名", "reason": "原因"}
    ],
    "watch_metrics": [
      {"letter": "A", "metric": "指标名（如月度销量）", "why": "为什么这个指标是关键先行信号"},
      {"letter": "B", "metric": "指标名", "why": "为什么关注"},
      {"letter": "C", "metric": "指标名", "why": "为什么关注"},
      {"letter": "D", "metric": "指标名", "why": "为什么关注"}
    ],
    "next_steps": [
      "下一步核验1：这份报告中尚未确认、建议后续去验证的事项",
      "下一步核验2"
    ],
    "conclusion": "板块综合结论，3-5 段，包括核心逻辑、催化剂、风险提示",
    "research_path": "一句话研究路径：给出一条可执行的研究路线，如'研究中先看XX→再跟XX→最后验证XX'",
    "market_blind_spots": "不是X，而是Y：指出市场共识之外被低估的约束或机会。用'不是A，而是B'句式点出认知偏差"
  },
  "segments": [
    {
      "name": "环节名",
      "positioning": "环节定位：在产业链中的位置、核心功能、价值量占比",
      "value_ratio": 19,
      "localization_progress": "国产化进展：国产化率、主要国内玩家、与海外差距",
      "evidence_sources": [
        {"source": "研报标题", "institution": "券商名", "date": "2026-06-21"}
      ],
      "barrier_type": "科技壁垒",
      "barrier_detail": "壁垒详细说明：技术难度、量产门槛、认证周期",
      "failure_conditions": [
        "条件1：什么事实出现会推翻该环节的看好逻辑",
        "条件2",
        "条件3"
      ],
      "international_landscape": {
        "主导厂商": "海外龙头企业及特点",
        "份额结构": "海外市占率分布",
        "技术/工艺代差": "海外与国内的技术/工艺差距",
        "进入壁垒": "进入该市场的核心障碍"
      },
      "domestic_landscape": {
        "主导厂商": "国内主要参与者",
        "份额结构": "国内市占率分布",
        "技术/工艺代差": "国内追赶进展",
        "进入壁垒": "国内企业面临的壁垒"
      },
      "product_tiers": [
        {"tier": "高端", "asp": "价格区间", "key_players": "主要玩家", "margin": "毛利率", "market_share": "市占率"},
        {"tier": "中端", "asp": "价格区间", "key_players": "主要玩家", "margin": "毛利率", "market_share": "市占率"},
        {"tier": "低端", "asp": "价格区间", "key_players": "主要玩家", "margin": "毛利率", "market_share": "市占率"}
      ],
      "profit_drivers": [
        {"driver": "利润驱动项（如原材料成本）", "weight": "高", "note": "说明为什么是关键驱动"},
        {"driver": "良率", "weight": "中", "note": "说明"},
        {"driver": "产品结构", "weight": "中", "note": "说明"},
        {"driver": "定价权/经营杠杆", "weight": "中", "note": "说明"}
      ],
      "tech_roadmap": [
        {"direction": "下一代技术方向", "timeline": "预计量产时间", "impact": "对竞争格局的影响"},
        {"direction": "替代技术风险", "timeline": "时间线", "impact": "如果发生会怎样"}
      ],
      "scoring_dimensions": [
        {"name": "不可替代性", "weight": "高"},
        {"name": "估值", "weight": "中"},
        {"name": "业绩", "weight": "中"},
        {"name": "客户", "weight": "高"},
        {"name": "管理层", "weight": "中低"}
      ],
      "stocks": [
        {
          "name": "公司名",
          "code": "688017",
          "role": "领先者",
          "irreplaceability": "高",
          "score": 85,
          "score_detail": {"不可替代性": 90, "估值": 65, "业绩": 80, "客户": 95, "管理层": 85},
          "eps_forecast": {
            "this_year": 1.23,
            "next_year": 1.56,
            "next_two_year": 1.89,
            "growth_rate": 26.8
          },
          "note": "结论依据"
        }
      ]
    }
  ]
}
```

**供应链说明**：`supply_chain` 的 `demand`、`upstream` 等字段必须来自研报中的实际产业链描述，不可使用模板示例值或凭空编造。

**评分规则**：
- `barrier_type` 取值："科技壁垒" 或 "产能壁垒" 或 "科技+产能双壁垒"
- `irreplaceability` 取值："高" / "中" / "低"
- `score` 取值 0-100，综合五维度加权
- 每个维度评分 0-100，由 Agent 根据研报中对公司在该维度的评述推断

**重要**：每个维度的分析必须有研报依据支撑，不能凭空编造。如研报信息不足，在 `note` 中注明"研报信息有限"。

**来源分级要求**：
- 在 `overview.conclusion` 末尾用一行标注来源强度
- 格式：`来源等级：强(N条) | 中(N条) | 弱(N条)`
- 强来源：年报/公告/官方统计/交易所披露/业绩会纪要
- 中来源：券商研报/行业期刊/可靠媒体/交叉验证的渠道调研
- 弱来源：社交媒体/KOL观点/无来源图表（仅作线索，不能作为结论依据）
- 对基于弱来源的结论，必须在 `note` 中注明"需进一步验证"

---

### Step 5: 生成 HTML

运行生成脚本：

```bash
# Windows 环境需设置编码，否则 Unicode 字符会报错
# Git Bash / Linux / macOS:
python "C:\Users\001\.workbuddy\skills\industry-report\scripts\build_report.py" \
  --data "analysis/{行业}/analysis.json" \
  --output "output/{行业}_产业研究报告.html"

# Windows CMD / PowerShell:
set PYTHONIOENCODING=utf-8 && python "C:\Users\001\.workbuddy\skills\industry-report\scripts\build_report.py" --data "analysis/{行业}/analysis.json" --output "output/{行业}_产业研究报告.html"
```

> **注意**：Windows 环境下所有 Python 脚本均需设置 `PYTHONIOENCODING=utf-8`，否则中文/emoji 等 Unicode 字符会导致 GBK 编码错误。

生成结束后，用 `present_files` 展示 HTML 文件给用户。

---

## 错误处理

| 场景 | 应对 |
|------|------|
| 两个数据源都不可用 | 告知用户需要配置 IWENCAI_API_KEY 或检查网络能访问东财 reportapi |
| IWENCAI_API_KEY 缺失（东财可用） | 自动降级仅用东财，在报告中注明"数据来源：东方财富" |
| 东财不可访问（iwencai 可用） | 正常使用 iwencai |
| iwencai API 返回 401 | Key 过期或无效，降级仅用东财 |
| API 返回空结果 | 告知用户该行业未找到研报，建议扩大范围或更换行业名 |
| 环节发现结果少于 3 个 | 告知用户研报数量不足以细分环节，建议用户手动指定环节 |
| 研报 URL 无法访问 | 使用 record 的 `content` 正文节选（第2层）或 `summary` 摘要（第3层），在报告中注明"内容基于节选/摘要分析" |
| 环节分类失败 | 用 `uncategorized.json` 保存未归类研报，提示用户人工确认 |
| 分析 JSON 不完整 | 标记缺失字段为空字符串，报告生成时显示"待补充" |
| Windows GBK 编码错误（UnicodeEncodeError） | 所有 Python 脚本前加 `PYTHONIOENCODING=utf-8` 环境变量 |

---

## 使用示例

### 示例 1：AI 自动发现环节

**用户**：帮我做人形机器人产业研究报告，最近 3 个月。

**Agent 执行**：
1. 解析：行业=人形机器人，环节=无（触发自动发现），时间=3 个月
2. 拉取 20 篇人形机器人研报，AI 分析标题发现高频关键词 → 识别出 6 个环节
3. 按 6 个环节采集研报
4. 读取研报，对各环节提取分析 → 写入 `analysis/人形机器人/analysis.json`
5. 生成 HTML → `present_files` 展示

### 示例 2：用户直接给环节

**用户**：查半导体设备，环节：光刻机、刻蚀设备、薄膜沉积、检测设备。

**Agent 执行**：
1. 解析：行业=半导体设备，4 个环节已给出 → 跳过发现步骤
2. 直接按 4 个环节采集研报
3. 后续同上

---

## 脚本说明

| 文件 | 功能 |
|------|------|
| `scripts/collect_reports.py` | **双数据源采集**：iwencai report-search（含 source_original 正文节选）+ 东方财富 reportapi（含 EPS 预测），双源合并去重 |
| `scripts/build_report.py` | JSON 数据注入 HTML 模板，动态渲染数据来源，生成最终报告（Windows 需 `PYTHONIOENCODING=utf-8`） |
| `templates/report.html` | 自包含 HTML 模板（CSS + JS 渲染，数据来源通过 `{{DATA_SOURCE}}` 占位符注入） |
| `references/format.md` | 分析字段详细说明和写作规范 |

---

## 关键约束

1. **环节来源**：要么用户提供，要么 AI 从研报中自动发现——二者必居其一，不能凭空编造
2. **发现后直接执行**：AI 自动发现的环节无需用户确认，直接进入数据采集
3. **供应链数据来自研报**：`supply_chain.demand`、`supply_chain.upstream` 等字段必须基于研报实际内容，不用模板默认值
4. **analysis.json 直接写入文件**，不要打印到 stdout（避免编码问题）
5. **所有路径使用绝对路径**
6. **评分必须有研报依据**，不能瞎编

## 反模式禁令（质量红线）

以下行为严格禁止：
1. **不要从泛泛的 SWOT 开始**——先给判断，再给依据
2. **不要在没有明确来源和指标时称公司为"龙头"**——必须引用研报原文或市占率数据
3. **不要把 TAM 增长等同于投资吸引力**——区分"市场变大"和"这个环节能赚钱"
4. **不要把客户敞口误认为客户锁定**——区分"有客户"和"客户无法离开"
5. **不要把收入增长当作稀缺性的证明**——收入增长可能是行业β，不是公司α
6. **不要用自信措辞掩盖弱证据**——对弱来源的结论必须注明"需进一步验证"
7. **不要把未核实的客户名称写到报告中**——只有研报明确提及且可交叉验证的客户才写
8. **不要省略"这个行业是什么"**——每个行业和环节的第一句话必须解释定义
9. **不要把所有事实都报一遍**——抓住少数真正改变判断的事实，不是堆砌数据
