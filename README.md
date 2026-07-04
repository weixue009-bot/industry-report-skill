# Investment Research Skill 🏭📈

AI 驱动投资研究报告生成器 —— 支持**行业产业分析**和**公司深度分析**两种模式。自动从同花顺 iwencai + 东方财富 reportapi + 发现报告 fxbaogao 三数据源拉取研报，结合同花顺官方 hithink-finance-query skill + 腾讯财经 qt.gtimg.cn 获取财务数据和实时行情，AI 分析后生成单文件自包含 HTML 报告。

用户只需说出行业名称或公司名称，其余全自动。

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
- 双源采集去重，支持 iwencai（需 Key）+ 东财（免费）

### 公司分析（Part B）

- 个股研报（qType=0 + 三源）+ 财务数据 + 行情估值
- 问财官方 hithink-finance-query skill（基本面+财务）+ 腾讯财经 qt.gtimg.cn（行情+日K线）
- 单页竖向卡片式布局，信息聚焦
- 一句话看懂 → 身份卡片 → 产业链定位 → 竞争对比 → 盈利逻辑 → 风险跟踪

---

## 数据源

| 数据源 | 认证 | 行业模式 | 公司模式 |
|--------|------|---------|---------|
| **同花顺 iwencai report-search** | 需 `IWENCAI_API_KEY` | 行业研报搜索 + 正文节选 | 个股研报搜索 |
| **同花顺 hithink-finance-query（官方 skill）** | 需 `IWENCAI_API_KEY` | — | 公司财务/基本面（官方专用财务 skill） |
| **东方财富 reportapi** | 免费公开 | 行业研报（qType=1） | 个股研报（qType=0，含 EPS） |
| **发现报告 fxbaogao.com** | 免费公开 | 行业/个股研报搜索，支持相对时间过滤 | 同左 |
| **腾讯财经 qt.gtimg.cn** | 免费公开，不封IP | — | 实时行情（PE/PB/市值/换手率）+ 日K线（前复权，250 日） |

三个数据源都可用时同时拉取并合并去重；部分不可用时自动降级。

---

## 快速开始

### 环境要求

- Python 3.8+
- API Key：`IWENCAI_API_KEY`（如需使用同花顺数据源，可从 iwencai.com/skillhub 获取）
- 可选：`FXBAOGAO_SSL_NO_VERIFY=1`（如 fxbaogao.com SSL 证书验证失败，限企业内部网络环境）

### 安装

```bash
git clone https://github.com/weixue009-bot/industry-report-skill.git
cd industry-report-skill
pip install requests
```

### 行业分析

```bash
# 采集研报数据
python scripts/collect_reports.py --mode industry \
  --industry "机器人" \
  --segments "丝杠,减速器,电机,传感器,灵巧手,具身智能模型" \
  --months 3 --size 10

# 生成 HTML 报告
python scripts/build_report.py --mode industry \
  --data "analysis/industry/机器人/analysis.json" \
  --output "output/industry/机器人_产业研究报告.html"
```

### 公司分析

```bash
# 采集研报数据
python scripts/collect_reports.py --mode company \
  --code "300059" --months 3 --size 20

# 采集财务 / 行情数据
python scripts/company_collect.py --code "300059"

# 生成 HTML 报告
python scripts/build_report.py --mode company \
  --data "analysis/company/300059/analysis.json" \
  --output "output/company/300059_东方财富_深度分析.html"
```

> **Windows 用户注意**：运行 Python 脚本时请设置 `PYTHONIOENCODING=utf-8` 环境变量。

---

## 项目结构

```
industry-report-skill/
├── SKILL.md                       # WorkBuddy Skill 定义（行业 + 公司双模式）
├── _meta.json                     # 技能元数据
├── CHANGELOG.md                   # 完整版本更新记录
├── LICENSE                        # MIT
├── README.md                      # 本文件
│
├── scripts/
│   ├── collect_reports.py         # 双数据源研报采集（--mode industry|company）
│   ├── company_collect.py         # 公司财务/行情数据采集（问财 + 东财双源）
│   └── build_report.py            # HTML 报告生成（双模板路由）
│
├── templates/
│   ├── report.html                # 行业分析 HTML 模板
│   └── company_report.html        # 公司分析 HTML 模板（竖向卡片式）
│
└── references/
    ├── format.md                  # 行业分析写作规范
    └── company_format.md          # 公司分析写作规范
```

### 输出文件隔离

```
{工作目录}/
├── raw/industry/{行业名}/      ← 行业原始数据
├── raw/company/{代码}/          ← 公司原始数据
├── analysis/industry/{行业名}/  ← 行业分析数据
├── analysis/company/{代码}/     ← 公司分析数据
├── output/industry/             ← 行业最终报告
└── output/company/              ← 公司最终报告
```

---

## 参考与致谢

本项目参考了 [Simon 林](https://github.com/simonlin1212) 的 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 项目，感谢 Simon 林对 A 股数据接口的整理与分享。

## License

MIT
