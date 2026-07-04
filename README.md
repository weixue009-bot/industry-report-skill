# Investment Research Skill 🏭📈

AI 驱动投资研究报告生成器 —— 支持**行业产业分析**和**公司深度分析**两种模式。自动从同花顺 iwencai + 东方财富 reportapi + 发现报告 fxbaogao 三数据源拉取研报，结合同花顺官方 hithink-industry-query（行业统计数据）和 hithink-finance-query（公司财务指标）skill + 腾讯财经 qt.gtimg.cn（实时行情），AI 分析后生成单文件自包含 HTML 报告。

用户只需说出行业名称或公司名称，其余全自动。

---

## 安装

### 1. 解压到 WorkBuddy Skills 目录

```bash
# 将 .zip 解压到以下位置（无该目录则新建）：
# Linux / macOS
mkdir -p ~/.workbuddy/skills/
unzip industry-report-skill.zip -d ~/.workbuddy/skills/

# Windows
# 解压到 C:\Users\{用户名}\.workbuddy\skills\industry-report\
```

### 2. 安装依赖的 Python 环境

```bash
# 确认 Python 版本
python --version   # 需要 >= 3.9
```

本技能无外部 Python 依赖（仅使用标准库 `urllib` / `json` 等），无需 `pip install`。

### 3. 安装同花顺官方数据 Skill（二选一，按需）

本技能依赖同花顺官方提供的行业/财务数据 API，需要先安装对应的 Skill：

```bash
# 安装同花顺 SkillHub CLI（如尚未安装）
pip install iwencai-skillhub-cli

# 安装财务数据 Skill（公司分析模式需要）
iwencai-skillhub-cli install hithink-finance-query

# 安装行业数据 Skill（行业分析模式需要）
iwencai-skillhub-cli install hithink-industry-query
```

> 如果只需要其中一种模式，可只装对应的 Skill。

### 4. 配置 API Key

```bash
# Linux / macOS
export IWENCAI_API_KEY="your_api_key_here"
echo 'export IWENCAI_API_KEY="your_key"' >> ~/.bashrc

# Windows PowerShell
$env:IWENCAI_API_KEY="your_api_key_here"
# 或通过系统环境变量永久配置
```

API Key 可从 [iwencai.com/skillhub](https://iwencai.com/skillhub) 获取。

### 5. 重启 WorkBuddy

安装完成后重启 WorkBuddy，Skill 会自动加载。在对话中输入"查 XX 行业"或"查 XX 公司"即可使用。

---

## 两种模式

| 模式 | 触发方式 | 输出 |
|------|---------|------|
| **行业分析** | "查XX行业""产业研究报告" | 产业链结构 + 环节分析 + 标的评分 + 策略建议 |
| **公司分析** | "查XX公司""个股深度分析" | 公司身份 + 产业链定位 + 竞争对比 + 盈利逻辑 + 风险反证 |

### 行业分析（Part A）

- 自动从研报中发现产业链细分环节
- 16 个分析模块（总览 + 各环节子页）
- 板块评分总览 / 核心标的池 / 产业链结构 / 竞争格局 / 证据来源
- 研报四源采集去重（iwencai + 东财 + fxbaogao）+ hithink-industry-query 行业统计数据

### 公司分析（Part B）

- 个股研报（qType=0 + 三源）+ 财务数据 + 行情估值
- 问财官方 hithink-finance-query skill（基本面+财务）+ 腾讯财经 qt.gtimg.cn（行情+日K线）
- 单页竖向卡片式布局，信息聚焦
- 一句话看懂 → 身份卡片 → 产业链定位 → 竞争对比 → 盈利逻辑 → 风险跟踪

---

## 数据源架构

| 数据源 | 认证 | 行业模式 | 公司模式 |
|--------|------|---------|---------|
| **同花顺 iwencai report-search** | 需 `IWENCAI_API_KEY` | 行业研报搜索 + 正文节选 | 个股研报搜索 |
| **同花顺 hithink-industry-query（官方 skill）** | 需 `IWENCAI_API_KEY` | 行业估值/财务/行情/板块排名查询（四源之一） | — |
| **同花顺 hithink-finance-query（官方 skill）** | 需 `IWENCAI_API_KEY` | — | 公司财务/基本面（官方专用财务 skill） |
| **东方财富 reportapi** | 免费公开 | 行业研报（qType=1） | 个股研报（qType=0，含 EPS） |
| **发现报告 fxbaogao.com** | 免费公开 | 行业/个股研报搜索，支持相对时间过滤 | 同左 |
| **腾讯财经 qt.gtimg.cn** | 免费公开，不封IP | — | 实时行情（PE/PB/市值/换手率）+ 日K线（前复权，250 日） |

**行业模式**：研报三源（iwencai + 东财 + fxbaogao）按关键词搜索并自动合并去重 + hithink-industry-query 独立查询行业统计数据（估值/行情/板块排名），四数据源并行。
**公司模式**：个股研报三源合并 + hithink-finance-query 查询财务指标 + 腾讯财经获取行情+K线，共五数据源并行。
所有数据源部分不可用时自动降级。

---

## 手动运行（在 skill 目录下执行）

如不想通过 Agent 调用，也可直接运行脚本：

### 行业分析

```bash
# 采集研报数据
cd ~/.workbuddy/skills/industry-report
python scripts/collect_reports.py --mode industry \
  --industry "机器人" \
  --segments "丝杠,减速器,电机,传感器,灵巧手,具身智能模型" \
  --months 3 --size 10

# AI 分析（需自行读取研报并生成 analysis/industry/机器人/analysis.json）

# 生成 HTML 报告
python scripts/build_report.py --mode industry \
  --data "analysis/industry/机器人/analysis.json" \
  --output "output/industry/机器人_产业研究报告.html"
```

### 公司分析

```bash
cd ~/.workbuddy/skills/industry-report

# 采集研报数据
python scripts/collect_reports.py --mode company \
  --code "300059" --months 3 --size 20

# 采集财务 / 行情数据
python scripts/company_collect.py --code "300059" --output-dir "."

# AI 分析（可先用 company_analysis.py 生成框架）
python scripts/company_analysis.py --code "300059" --work-dir "."
# 然后补全 analysis/company/300059/analysis.json 的文本字段

# 生成 HTML 报告
python scripts/build_report.py --mode company \
  --data "analysis/company/300059/analysis.json" \
  --output "output/company/300059_东方财富_深度分析.html"
```

> **Windows 用户注意**：运行 Python 脚本时请设置 `PYTHONIOENCODING=utf-8` 环境变量。

---

## 参考与致谢

本项目参考了 [Simon 林](https://github.com/simonlin1212) 的 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 项目，感谢 Simon 林对 A 股数据接口的整理与分享。

## License

MIT
