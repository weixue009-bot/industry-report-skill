  # Changelog

  ## [2.0.6] - 2026-07-04

  ### Fixed
  - **公司报告竞争对比卡片公司名写死**：`company_report.html` 中"和谁比较才合理"卡片的「{公司}的位置」标签和「与{公司}的差距」表头硬编码为"华微电子"，导致非华微公司（如东方财富）报告渲染错位。改为动态读取 `d.company_name`，两个全球对标 fallback 文案中的"华微"也同步替换。

  ---

  ## [2.0.5] - 2026-07-04

  ### Fixed
  - **公司模式 iwencai 搜索崩溃**：`collect_company_reports()` 把 `call_iwencai()` 返回的 `(status, payload)` 元组当 list 迭代，触发 `'int' object has no attribute 'get'`，导致 iwencai 个股研报长期返回 0。修复后正确解包 + 调 `parse_iwencai_report()` 规范化字段。东方财富验证：iwencai 0 → 21 篇。
  - **产业链流程图 fallback 数据错位**：东方财富分析 JSON 缺 `chain_flow` 字段时，模板 fallback 显示华微电子的"硅片/碳化硅衬底"半导体产业链内容。已为东方财富和华微电子的 `analysis.json` 显式补充 `chain_flow` 字段。
  - **盈利逻辑卡片序号遮挡文字**：旧版用 32px 大号水印（绝对定位右上角）覆盖标题区域，导致长文本被遮挡。改为卡片顶部左侧小号角标 "NO.0X"（11px 蓝色 70% 透明度），左侧色条移到左边竖向展示，标题独占整行不被覆盖

---

## [2.0.3] - 2026-07-04

### Changed
- **竞争对比合并为单卡**：全球对标 + 国内对比合并为一张「和谁比较才合理」卡片，上方为公司定位栏，下方为统一表格（对标公司 | 定位与实力 | 与华微的差距）
- **盈利逻辑 UI 升级**：从简单列表改为 3 列卡片式布局，带序号水印（01/02/03）和顶部色条，视觉层次更丰富
- **全局细节优化**：
  - 标题栏加左侧 4px 竖线装饰（card h2::before）
  - 元信息行加圆点分隔符（meta .dot）
  - 身份卡片加悬停效果（identity-item :hover）
  - 业务卡片加悬停边框（biz-card :hover）、占比改为标签样式
  - 产业链中游盒子 highlighted（chain-box.highlight）
  - 间距统一：header padding 40→44px，card margin-bottom 20→24px，全局 spacing 更宽松
  - 风险列表从 border-bottom 改为 gap 间距排布

---

## [2.0.2] - 2026-07-04

### Changed
- **`templates/company_report.html` 界面重构**：参考研究卡片布局（康宁公司案例），重新设计公司深度分析模板
  - 单页竖向卡片式结构，信息流更聚焦
  - 保留现有配色方案（深色 header #1a1a2e + 白色卡片 + 蓝色强调色）
  - 精简卡片数量，移除机构研报矩阵和 EPS 预测与一致性预期卡片
  - 新增模块：一句话看懂、公司身份、产业链定位、核心概念关系、增量驱动、业务拆分、竞争对比、盈利逻辑、证据/卡点、关键跟踪指标、研究路径、风险反证
- **`references/company_format.md` 精简**：数据模型从 20+ 字段精简到 14 个核心字段，明确 v2.2 已弃用字段（reports/eps_forecast/moat/growth_mechanism/valuation 对象）
- **华微电子 analysis.json 重写**：按新字段模型生成，数据更聚焦、更结构化

### Fixed
- 报告生成后不再展示空白的"机构研报矩阵"和"EPS 预测"占位卡片

---

## [2.0.1] - 2026-07-04

### Fixed
- **`company_collect.py` fetch_profile() 名称/行业返回错误**：旧版 name 字段返回股票代码而非中文简称（f57/f58 映射错误），industry 字段返回空。修复：切换为主力数据源问财 iwencai query2data API（获取名称/行业/上市日期/主营/PE/PB），东财 push2 仅辅助行情快照（价格/成交量）
- **`company_collect.py` fetch_financial() 返回全空**：东财 datacenter API (`RPT_F10_FINANCE_MAINFINADATA`) 不可靠，替换为问财 iwencai query2data 查询（ROE/毛利率/净利率/营收/利润/同比/每股指标），12 个财务字段全部恢复正常

### Changed
- `company_collect.py` 数据源架构从"东财为主"改为"问财 iwencai（主力）+ 东财 push2（辅助）"，提升可靠性和字段完整性
- 新增 `_iwencai_query()` / `_extract_number()` / `_extract_str()` 工具函数，统一问财数据解析
- 移除 `fetch_industry_info()` 和独立的 `fetch_quote()`，合并进 `fetch_profile()` 双源逻辑
- 验证：华微电子（600360）四类数据全部正确返回（名称/行业/PE/PB/ROE/毛利率等）

---

## [2.0.0] - 2026-07-03

### Added
- **公司分析模式**：Skill 新增 `--mode company` 分支，支持个股深度分析（个股研报 + 财务数据 + 行情估值 + AI 分析 → HTML 报告）
- **`scripts/company_collect.py`**（新建）：公司非研报数据采集模块。对接东方财富免费接口，提供 `fetch_profile()`/`fetch_financial()`/`fetch_valuation()`/`fetch_kline()` 4 个核心函数。输出到 `raw/company/{代码}/`
- **`templates/company_report.html`**（新建）：公司分析独立 HTML 模板（约 320 行），含公司名片、一句话判断、研报矩阵、EPS 预测柱状图、财务基本面、护城河分析、增长机制、风险反证、证据来源等级等模块。UI 沿用行业模板配色体系，不影响现有行业模板
- **`references/company_format.md`**（新建）：公司分析 analysis.json 完整字段定义和写作规范（profile_info/financial/valuation/moat/risks/evidence_sources 等）
- **triggers 追加**：SKILL.md 新增"公司深度分析""查XX公司""查XX股票""个股研报""股票分析""公司研究""这家公司怎么样"等公司分析入口关键词

### Changed
- **`collect_reports.py`**：新增 `--mode` 参数（industry/company）；`--mode company` 按股票代码采集个股研报（qType=0 + iwencai 自然语言搜索）；`--mode industry` 输出路径改为 `raw/industry/{行业名}/`
- **`build_report.py`**：新增 `--mode` 参数与双模板路由逻辑；`load_template()` 根据 mode 自动选择 report.html 或 company_report.html
- **SKILL.md**：拆分为 Part A（行业模式）+ Part B（公司模式）两条独立工作流，含完整的数据模型和 Step-by-step 流程
- **文件隔离策略**：行业数据走 `raw/industry/`、`analysis/industry/`、`output/industry/`；公司数据走 `raw/company/`、`analysis/company/`、`output/company/`。三层统一隔离
- **CHANGELOG.md**：新增 v2.0.0 条目

### Fixed
- `build_data_source()` 移除已废弃的 index.json fallback 逻辑（v1 遗留），统一从 analysis.json 读取 sources_used

---

## [1.3.0] - 2026-07-03

### Added
- **源_original 正文节选字段**：collect_reports.py 的 iwencai 解析器新增 `content` 字段映射（对应 API 的 `source_original`），500-2000 字正文节选，远丰富于 200-300 字的 summary。
- **东财 EPS 预测字段**：collect_reports.py 的东财解析器新增 `eps_this_year` / `eps_next_year` / `eps_next_two_year` 字段（来自 API 的 `predictThisYearEps` 等），为个股分析引入券商盈利预测。
- **环节子页 EPS 列**：股票表格新增「盈利预测（EPS）」列，动态检测是否有数据后自动显示，格式为 `1.23→1.56` + `+26.8%`（红涨绿跌）。
- **统一 record 字段声明注释**：collect_reports.py 模块头部新增全部 16 个字段的定义和类型注释。
- `references/format.md` 新增「EPS 预测」专节。

### Changed
- **Step 4.1 研报读取升级为三层策略**：第1层 WebFetch 全文（最新 3 篇）→ 第2层 `content` 正文节选（500-2000 字）→ 第3层 `summary` 摘要（200-300 字），分析深度显著提升。
- **analysis.json stocks[] 结构新增 `eps_forecast` 可选字段**：含 `this_year` / `next_year` / `next_two_year` / `growth_rate`.
- **SKILL.md**：Step 4.1 三层读取说明、stocks 数据模型同步、脚本说明表更新、错误处理表更新。
- **模板 CSS**：新增 `.col-eps` / `.eps-line` / `.eps-growth` 样式。

---

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
