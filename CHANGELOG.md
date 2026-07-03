# Changelog

## [1.2.2] - 2026-07-03

### Fixed
- **竞争格局卡片 4 行精准等高（改进版）**：v1.2.1 的 `align-items:stretch` + `min-height:56px` 方案行高不够精确。升级为 `.landscape-rows` 使用 `display:grid; grid-template-rows: repeat(4, 1fr)` 强制四行各占 25% 高度；`.landscape-key` 加右框分隔；`.two-col .card` 加 `display:flex;flex-direction:column` 保证卡片组件上下垂直对齐。左右两张竞争格局卡片的 4 行逐行严格对齐。

---

## [1.2.1] - 2026-07-03

### Fixed
- **环节子页首屏价值量占比匹配为 0%**：原 `cost_breakdown` 用详细名（"无框力矩电机"、"力传感器"），但 segments 用简称（"电机"、"传感器"），名称不匹配导致 `ratio_map.get(name, 0)` 全返回 0。修复：增加 `value_ratios` 显式映射表（丝杠19 / 减速器13 / 电机16 / 传感器11 / 灵巧手6 / 具身智能模型3）。
- **竞争格局大量字段"待补充"**：原 `parse_landscape()` 自动解析函数过简陋，正则只匹配到「主导厂商」。改为手工为 6 个环节完整补充 4 个字段（主导厂商/份额结构/技术/工艺代差/进入壁垒）。
- **总览产业链核心环节价值量占比未同步**：`supply_chain.core_segments` 旧数据中"丝杠"等没有价值量后缀，改为"丝杠（19%）"等带括号百分比，模板自动拆分为加粗标题+灰色占比描述。

### Changed
- 写作规范明确：`value_ratio` 数字不带 `%` 符号；`localization_progress` 80-150 字；竞争格局建议写结构化对象。

---

## [1.2.0] - 2026-07-03

### Changed
- **环节子页首屏三卡片布局**：原来的单卡片「环节定位」改为左侧「环节定位」+ 右上「价值量占比」+ 右下「国产化进展」三卡片组合，信息密度更高。
- **竞争格局结构化**：国际竞争格局 / 国内竞争格局两张卡片不再显示一段长文本，而是统一按 4 个字段分条展示：主导厂商、份额结构、技术/工艺代差、进入壁垒。
- **产业链核心环节显示价值量占比**：`supply_chain.core_segments` 支持在环节名后加 `（占比%）`（如"丝杠（19%）"），模板会自动拆分为加粗标题 + 灰色占比描述。

### Added
- `analysis.json` 中每个 segment 新增字段：
  - `value_ratio`：该环节价值量占比（%）
  - `localization_progress`：国产化进展描述
  - `evidence_sources`：该环节内容的证据来源列表，每项包含 `source`（研报标题）、`institution`（券商/来源）、`date`（可选）
- `analysis.json` 中 `international_landscape` / `domestic_landscape` 支持结构化对象：{"主导厂商": "...", "份额结构": "...", "技术/工艺代差": "...", "进入壁垒": "..."}。旧版字符串仍可兼容显示。
- 新增「证据来源」卡片：环节子页底部展示该环节内容引用的研报列表。
- 新增 CSS 类：`.segment-top`、`.pos-card`、`.metric-card`、`.landscape-card`、`.landscape-rows`、`.evidence-card`、`.evidence-list` 等。
- `formatItem()` 支持中英文括号 `"标题(说明)"` 和 `"标题（说明）"` 两种写法。

### Fixed
- 产业链盒子"标题（说明）"格式使用中文括号时无法拆分的问题。

---

## [1.1.0] - 2026-07-03

### Fixed
- **数据来源动态渲染**：模板不再硬编码"数据来源：同花顺i问财"，改为 `{{DATA_SOURCE}}` 占位符。`build_report.py` 新增 `build_data_source()` 函数，根据实际使用的数据源（iwencai/eastmoney）和篇数动态生成，如"数据来源：同花顺i问财（46篇） + 东方财富（3篇）"。从 `index.json` 或 `analysis.json` 读取 `sources_used` / `source_stats`。
- **Windows GBK 编码兼容**：运行 `collect_reports.py` 和 `build_report.py` 需设置环境变量 `PYTHONIOENCODING=utf-8`，避免 Unicode 字符编码错误。
- **核心标的池表格溢出**：修复 td 全局 `white-space: nowrap` 导致入选逻辑列文本溢出表格的问题，改为百分比列宽（25%/18%/auto），入选逻辑列 `white-space: normal` + `word-break: break-word`。

### Changed
- **「板块评分总览」双栏模式优化**：在 `.two-col` 容器内，评分指标从网格布局改为单列横向行式（名称-分数-进度条-说明），与右侧核心标的池等高时不留空白。
- **「先分清三件事」卡片化**：表格横向排布 → 网格卡片布局（`concept-grid` / `concept-card`），每个维度独立卡片，hover 上浮效果，标题文字根据维度数自动调整。
- **「核心标的池」表格化**：卡片列表 → 分组表格（`pool-table`），三列固定比例（名称/代码 25% / 细分环节 18% / 入选逻辑 auto），表头 nowrap 单行。
- **「产业链结构」Grid 化**：flex-wrap → CSS Grid 固定列数（根据项目数自动匹配1-6列），支持"标题(说明)"拆分为加粗标题 + 灰色描述的盒子内部格式。
- **环节详表「角色」列**：加 `white-space: nowrap` 固定宽度84px，保证领先者/追赶者 tag 单行不换行。

### Added
- `analysis.json` 新增 `sources_used`（数据源列表）和 `source_stats`（各源篇数）字段。
- `build_report.py` 新增 `{{DATA_SOURCE}}` 模板占位符替换。
- `.two-col .score-grid` / `.score-item` 横向行式系列 CSS。
- `.concept-grid` / `.concept-card` / `.concept-points` 卡片网格系列 CSS。
- `.pool-table` / `.pool-stock` / `.pool-code` / `.col-logic` 表格系列 CSS。
- `.sc-grid-1` ~ `.sc-grid-6` 产业链 Grid 列数类。
- `.sc-box-title` / `.sc-box-desc` 产业链盒子双行格式支持。
- `formatItem()` JS 函数：解析"标题(说明)"格式并拆分渲染。

---

## [1.0.0] - 2026-07-03

### Added
- 双数据源平级采集架构（同花顺 iwencai report-search + 东方财富 reportapi）
- 自动环节发现：AI 从研报标题和摘要中识别产业链细分环节
- 17 模块深度分析结构：核心判断、命题、行业定义、概念厘清、产业链结构、板块评分、核心标的池、价值量构成、盈利逻辑、关键约束、环节优先级、兑现进度、跟踪指标、核验清单、市场盲点、研究路径、结论建议
- 单文件自包含 HTML 报告模板，CSS + JS 全部内联，零外部依赖
- 双源去重机制（uid + 标题+日期联合去重）
- 东财 reportapi 接入：行业研报（qType=1）按关键词过滤，免费公开无需 Key
- 自动数据源检测与降级：双源都可用时合并，仅一个可用时自动降级
- Tab 切换子栏目内容渲染
- 板块评分总览与核心标的池左右两栏布局
- 产业链结构 flexbox 自适应三层布局（需求端/核心环节/上游）
- 环节页面含定位、竞争格局、产品分层、壁垒类型、失败条件、评分维度、技术路线图、核心标的表

### Fixed
- 修复切换子栏目时因 `scoreFn` 未定义导致内容不更新的 Bug
- 优化核心标的表列宽，添加 `<colgroup>` 固定各列最小宽度
- 评分/分项列改为居中对齐，备注列支持换行

### Changed
- `_meta.json` 标注依赖环境变量 `IWENCAI_API_KEY`
- `SKILL.md` 新增双数据源说明、降级策略
- `collect_reports.py` 重构为双数据源架构

---

## [0.1.0] - 2026-03

### Added
- 项目初始化，基于 iwencai report-search 单数据源
- 基础采集脚本 `collect_reports.py`
- HTML 生成脚本 `build_report.py`
- 基础 HTML 模板
- 分析字段写作规范 `references/format.md`
