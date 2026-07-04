  # Changelog

  ## [2.6.0] - 2026-07-04

  ### Added

  - **集成 hithink-industry-query（同花顺官方行业数据 skill）到行业分析模式**：
    - `collect_reports.py` 新增 `call_hithink_industry()` + `fetch_industry_stats()`：采集行业估值/板块行情/环节个股指标等结构化数据
    - 采集流程新增第 4 数据源管道：研报采集完成后自动调用 hithink-industry-query，输出到 `raw/industry/{行业}/industry_stats.json`
    - SKILL.md Step 4 新增行业统计数据读取要求：AI 在评分"估值位置""资金动向"维度时，必须引用 `industry_stats.json` 的实际数据

  ### Changed

  - **`collect_reports.py` 数据源架构**：从"研报三源"扩展为"研报三源 + 行业统计数据"四源架构
  - **`SKILL.md` Step 3 数据源表**：更新为"四个数据源架构"，新增 hithink-industry-query 条目
  - **`SKILL.md` Step 4.1**：新增"行业统计数据读取"小节，含字段映射表和评分引用示例

  ### Technical

  - `call_hithink_industry()`：使用 `X-Claw-Skill-Id: hithink-industry-query` Header，URL `openapi.iwencai.com/v1/query2data`
  - `fetch_industry_stats()`：3 个查询（行业估值 / 板块行情 / 按环节个股指标），每环节间隔 0.5s
  - `industry_stats.json` 结构：`{valuation: [], momentum: [], seg_valuation: {环节名: {...}, ...}}`

  ## [2.5.1] - 2026-07-04

  ### Changed

  - **问财财务数据源从自实现 `_iwencai_query` 切换为官方 `hithink-finance-query` skill**：通过 Iwencai SkillHub CLI 安装同花顺官方财务数据技能，`company_collect.py` 的 `IWENCAI_SKILL_ID` 从 `hithink-market-query` 改为 `hithink-finance-query`，查询语句和字段名映射同步适配官方返回格式。

  ### Technical

  - 安装路径：`~/.iwencai-skillhub/skills/hithink-finance-query/`
  - CLI 路径：`~/.local/bin/iwencai-skillhub-cli`
  - 与旧方案差异：官方 skill 使用 `X-Claw-Skill-Id: hithink-finance-query` Header，字段名更稳定（如 `归母净利润同比增长率` 而非自解析 `归属母公司股东的净利润(同比增长率)`）

  ## [2.5.0] - 2026-07-04

  ### Changed

  - **产业链结构卡片流水线翻转自上而下**：`renderSupplyChain()` 改为 `上游材料与设备 → 核心环节 → 需求端`（原为需求端→核心→上游，箭头方向与产业逻辑相反）。箭头均向下，SVG 箭头的 `<line y1/y2>` 方向统一为 top→bottom。
  - **核心环节配色从固定7色改为 HSL 色相动态生成**：旧版 `coreColors` 固定 7 色数组（`['#e74c3c','#e67e22','...']`），环节超 7 时颜色重复。新版 `genCoreColors(n)` 从 200°(蓝) 到 120°(绿) 连续 280° 渐变，饱和度 60%/亮度 50%；相邻环节色相自然过渡，N 个环节 N 色互不重复。

  ### Removed

  - **`renderSupplyChain()` 的 `coreItems` fallback 逻辑**：旧版 `const coreItems = core.length >= segNames.length ? core : segNames` 在 core_segments 数量少于 segments 数量时，自动用 `segments[].name` 替换全部 core_segments，隐藏了数据层不一致。新版直接用 `core`，核心环节显式渲染 `core_segments`，要求必须与 `segments[]` 对齐（已在 format.md 约束）。

  ## [2.4.1] - 2026-07-04

  ### Fixed

  - **Write 工具大文件截断导致 analysis.json 字段丢失**：有色金属 `analysis.json`（~60KB）在初始写入时被静默截断，铜/黄金/铝 3 个 segment 的 `stocks`（9只标的）和 overview 的 `core_stock_pool`（13只标的）全部丢失。修复：通过 Python 脚本 `json.dump()` 方式补回。

  ### Added

  - **`references/format.md` 新增「大文件写入规范」**：明确 Write 工具有 ~30-40KB 限制，规定 4 条规则（分步编码 / 逐 segment 写 / 写入后校验 / 尾部字段优先检查）和示例校验命令。

  ## [2.4.0] - 2026-07-04

  ### Changed
  - **公司分析字段规范全面升级（v2.3 → v2.4 模板驱动版）**：基于三家公司（华微电子/东方财富/上海机电）的实战修复经验，将 company_format.md 从"简陋文档"升级为"模板驱动全字段清单"。
    - 依模板代码（company_report.html 第 274-398 行）梳理 18 个顶层字段的精确类型和嵌套结构
    - 新增"字段格式规则"章节，用上海机电修复案例逐一标注 5 个最高频错误
    - 新增"常见错误清单"表格（8 条错误，每条含表现/根因/修正格式）
    - 新增"完整 analysis.json 模板"（可逐字段对照填写）
    - 新增"检查清单"（18 个 ✓ 条目，写完后逐一勾选）
    - 弃用 `financial_snapshot` 字段（模板不渲染），从完整模板中移除
  - **SKILL.md Step B3**：数据模型后新增 5 条校验清单 + 新增「公司 analysis.json 字段格式校验清单」⚠️ 醒目区块
  - **验证**：上海机电 v1（4 处字段缺失/格式错误）→ v2（全部修复，30KB 完整报告）

  ---

  ## [2.3.0] - 2026-07-04

  ### Changed
  - **公司行情数据源：东财 push2 → 腾讯财经 qt.gtimg.cn**：`company_collect.py` 的 `fetch_profile()` 移除东财 push2 行情快照调用，改为 `tencent_quote()` 函数接入腾讯财经免费实时行情接口。
    - **动机**：东财 push2 在该环境下经常返回错误的 PE/PB/市值数值（如 PE=6203 而非 81.7），且名称字段只返回代码。腾讯财经接口无需 Key、不封 IP、数据干净无需 /100 缩放。
    - **新增字段**：`turnover_pct`（换手率）、`amplitude_pct`（振幅）、`vol_ratio`（量比）、`pe_static`（PE 静）、`market_cap_yi`/`float_mcap_yi`（市值·亿元）、`limit_up`/`limit_down`（涨跌停价）、`last_close`（昨收）、`change_amt`（涨跌额）。
    - **验证**：华微电子 PE=81.7/PB=4.11/换手率 19.37% ✅；濮耐股份 PE=104.65/PB=1.3/换手率 6.04% ✅。
    - **K线数据源同步切换：东财 push2his → 腾讯财经**：`fetch_kline()` 改为调用 `web.ifzq.gtimg.cn/appstock/app/fqkline/get`（前复权日K线，字段:[date,open,close,high,low,volume]），移除 `_secid()` 函数。验证：华微电子 K线 0→250 日 ✅。
    - **东财 push2 / push2his 已从 `company_collect.py` 完全移除**，公司模式 100% 腾讯财经+问财双源。
    - 东财 push2his K线采集保留不变。

  ---

  ## [2.2.2] - 2026-07-04

  ### Fixed
  - **format.md / SKILL.md 缺少 segment 全字段清单**：根因修复——之前创新药 segment 缺 5 个字段的本质原因不是某一篇报告的疏忽，而是写作规范文档没有列出模板渲染所需的全 14 个 segment 字段。
  - `references/format.md`：新增「segment 全字段清单」表格（14 字段 - 模板渲染卡片映射）+ `profit_drivers` 专节 + `tech_roadmap` 专节 + `scoring_dimensions` 专节；清理「产品分层」重复/错位的旧内容。
  - `SKILL.md`：segment 数据模型示例前新增醒目注释（9 张卡片渲染顺序 + 必填提示）+ 数据模型后新增全字段清单对照表。

  ---

  ## [2.2.1] - 2026-07-04

  ### Fixed
  - **创新药 segment 缺失 5 个字段，导致子环节页卡片不完整**：4 个 segment 均缺少 `product_tiers`（产品分层表格）、`profit_drivers`（利润驱动表）、`tech_roadmap`（技术路线图）、`scoring_dimensions`（评分维度权重）和 `evidence_sources`（证据来源）等 5 个模板渲染所需字段，导致子环节页面只显示首屏三卡片+竞争格局+壁垒+失败条件，比机器人报告少 5 个核心卡片模块。
  - 修复：编写 `patch_segment_fields.py` 为 CXO/出海/ADC/创新中药 4 个环节逐项补全 5 个字段（3 层产品分层、4 项利润驱动、3 条技术路线、5 维评分权重、3-5 条证据来源），所有内容基于 150 篇三源研报数据编写。
  - 报告从 77KB → 93.8KB（+22%），子环节页面格式现在与机器人报告完全对齐。

  ---

  ## [2.2.0] - 2026-07-04

  ### Added
  - **第三数据源：发现报告 fxbaogao.com**：`collect_reports.py` 新增 `call_fxbaogao_reports()` 函数，调用 `api.fxbaogao.com/mofoun/report/searchReport/searchNoAuth` 搜索研报（免费公开接口，无需 Key）。支持 `--time last3mon` 等相对时间过滤，按行业名+环节关键词多轮搜索后去重合并。`build_report.py` 的 `build_data_source()` 同步新增"发现报告"标签。
  - 验证：创新药三源采集 **36 → 150 篇**（4x 提升），其中 fxbaogao 贡献 114 篇

  ### Changed
  - `collect_reports.py` 新增 `import html, re, ssl`；新增 `_fx_strip_html()` / `_fx_clean_snippet()` / `check_fxbaogao_available()` / `_build_fx_ssl_context()` 等 fxbaogao 辅助函数
  - `collect_reports()` 新增数据源 3 采集块，`collect_company_reports()` 同步接入
  - `source_stats` 字典新增 `"fxbaogao"` key

  ## [2.1.3] - 2026-07-04

  ### Fixed
  - **环节研究优先级与核心环节数量不一致**：总览"环节研究优先级"显示4个环节（ADC/双抗、CXO产业链、出海型创新药企、创新中药），但"核心环节"只有3个（缺"出海型创新药企"）。修复：`analysis/industry/创新药/analysis.json` 新增"出海型创新药企"为第4个 segment，含完整的 positioning/value_ratio/localization_progress/international_landscape/domestic_landscape/stocks 字段；`supply_chain.core_segments` 更新为4项（顺序与 segment_priority 一致）；`collect_reports.py` `_SEGMENT_KEYWORDS` 新增"出海型创新药企"扩展关键词（出海/海外/全球/license/bd/fda/百济/信达/传奇等）。

  ## [2.1.2] - 2026-07-04

  ### Fixed
  - **数据来源显示旧版东财篇数**：`analysis.json` 的 `source_stats` 未随采集脚本更新同步刷新（仍显示 eastmoney=2），导致报告 header 显示"东方财富（2篇）"而非实际的 26 篇。修复：`analysis/industry/创新药/analysis.json` 的 `source_stats` 更新为 `{iwencai: 10, eastmoney: 26}`，`source_report_count` 更新为 36。
  - **核心环节价值量占比 pill 位置和 UI**：旧版 pill 用绝对定位在 box 右上角，遮挡标题文字。修复：改为文档流排列（title → desc → pill），CSS 从 `position:absolute` 改为 `margin-top:8px`，视觉上在文字下方独立显示；pill 样式改为圆角胶囊（`border-radius:10px` + `letter-spacing:0.5px`），与 box 颜色协调。

  ## [2.1.1] - 2026-07-04

  ### Changed
  - **东财研报采集从标题关键词过滤改为行业分类字段过滤**：旧版 `call_eastmoney_industry_reports` 用 `industry_keywords`（segment name 列表）对标题做子串匹配，导致东财研报因标题不含指定 segment name 而被大量漏掉（创新药仅2篇）。修复：
    - 新增 `_INDUSTRY_NAME_KEYWORDS` 字典：每个行业定义宽泛关键词列表（如创新药→医药/生物/创新/CXO/ADC/抗体/PD-1等）
    - 过滤逻辑改为双重匹配：`industryName` 字段匹配（最可靠）+ 标题关键词匹配（补充），任一命中即保留
    - 移除 `industry_keywords` 参数，改用 `industry` 参数
    - 创新药验证：东财 2 → 26 篇（13x 提升）
  - **segment 分类扩展关键词匹配**：`match_segment()` 新增第二轮模糊匹配，用 `_SEGMENT_KEYWORDS` 字典（每个 segment 定义扩展关键词）匹配 title + summary + content 全文。解决东财研报标题不含 segment name 的分类问题

  ## [2.1.0] - 2026-07-04

  ### Fixed
  - **总览核心环节与子环节页数量不一致**：模板的 `renderSupplyChain` 用 `core.length >= segNames.length ? core : segNames` 决定展示项，导致 core_segments 数量可大于子环节数。修复：让用户分析阶段保证 `supply_chain.core_segments` 和 `segments[].name` 一一对齐，并通过模板的 `lookupRatio()` 模糊匹配（item 含 segment.name 或反向包含）保证 value_ratio 始终能挂上。
  - **核心环节不显示价值量占比**：`renderLayer()` 只显示 formatItem 拆出的标题/描述，没有从 segments 数组读取 value_ratio。修复：renderLayer 在 `layerType === 'core'` 时按 f.title 查 lookupRatio，找到就在 box 右上角加白色 pill 标签显示百分比；通过模糊匹配兼容 core_segments 名称与 segment.name 不完全一致的情况。验证：创新药核心环节现显示「CXO/CDMO 20%」「ADC/双抗 30%」「创新中药 8%」三个白色 pill。
  - **创新药 core_segments 包含「靶点发现与药物设计」造成环节错位**：「靶点发现与药物设计」属于研发流程不是产品环节，且 segments 数组里没有对应子环节。已在 `analysis/industry/创新药/analysis.json` 中移除该条目，core_segments 现为「CXO/CDMO、ADC/双抗、创新中药」3 个，与子环节 Tab 完全一致。
  - **价值量构成页面文字列宽过窄**：`cost-row` 用 flex+60px 固定 width，导致长文本在窄列里强行换行。修复：改为 `grid-template-columns: 120px 1fr 320px`（三列固定比例：标签 / 进度条 / 说明），`.cost-note` 单独成列（320px 宽 + 左侧分隔线），长文本自然换行。整行有浅灰背景（#f8f9fc）和圆角，可读性显著提升。验证：创新药「临床CRO费用」行说明「包括临床运营、数据管理、生物统计等」已正常换行显示。
  - **core_segments 名称与 segment.name 不匹配导致价值量占比不显示**：创新药的 core_segments 用「CXO/CRO/CDMO」「ADC/双抗等前沿技术平台」但 segment.name 是「CXO产业链」「ADC/双抗前沿技术」，lookupRatio 模糊匹配失败。修复：`analysis/industry/创新药/analysis.json` 中 core_segments 名称改为与 segment.name 完全一致（`"CXO产业链（研发生产外包）"`）；`references/format.md` 新增「核心环节命名规则」章节；`SKILL.md` 关键约束追加第 7 条。

  ## [2.0.9] - 2026-07-04

  ### Fixed
  - **价值量占比 metric-desc 硬编码"占人形机器人BOM成本"**：`templates/report.html` 第 596 行硬编码"占人形机器人BOM成本约"作为通用 metric-desc 文本。导致非机器人行业报告（创新药、CXO、锂电池、光伏等）显示机器人产业链描述，造成严重跨行业数据污染。修复：改为按 `DATA.industry` 动态匹配（人形机器人/工业机器人/创新药/CXO/半导体/新能源/光伏/锂电池等），未匹配的行业用 `占{行业名}产业总价值` 中性占位。验证：创新药报告 ADC/双抗环节现显示"占创新药管线总价值约30%"。
  - **iwencai API 不按日期严格过滤**：旧版 `--months 3` 实际只控制 API 行为，没有客户端过滤。实测创新药 44 篇中只有 13 篇（30%）是近 3 个月，70% 是早期研报，最早追溯到 2022 年。修复：`collect_reports.py` 在 `collect_reports()` 和 `collect_company_reports()` 顶部计算 `cutoff_date_str`（now - months*30 天），iwencai 循环里按 `report["date"] < cutoff_date_str` 过滤。验证：创新药 44 → 12 篇，全部为近 3 个月内；东财接口本身已按 beginTime 严格过滤，不受影响。

  ## [2.0.8] - 2026-07-04

  ### Changed
  - **增量驱动标签从圆形 → 胶囊形**：`.driver-impact` 改为 `min-width:48px; height:28px; border-radius:14px; padding:0 12px`，原先 44×44 圆里单字"高/中/低"显示拥挤，改为胶囊形后三档视觉一致、辨识度更高。新增 `.driver-impact.low{background:#7f8c8d}`（之前缺色，"中"和"低"实际渲染不一致）。
  - **「一句话看懂」行文风格调整**：建议从"不是A，而是B"句式改为更自然的"X是A，关键看B"句式，理由是连续多报告里"不是...而是..."读起来拗口、句式生硬。新生成的濮耐股份报告已应用此风格。

  ---

  ## [2.0.7] - 2026-07-04

  ### Fixed
  - **`chain_flow` fallback 残留华微电子产业链数据**：`company_report.html` 第 312 行硬编码了"硅片/碳化硅衬底→中游·华微电子→新能源车/光伏"作为通用 fallback（开发测试残留）。任何缺 `chain_flow` 字段的分析 JSON 都会显示华微电子的半导体产业链内容，造成严重的跨行业数据污染。修复：fallback 改为中性占位提示"请在 analysis.json 中填写 chain_flow 字段"。

  ---

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
