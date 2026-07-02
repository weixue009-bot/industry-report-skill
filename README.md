# Industry Report Skill 🏭

AI 驱动产业研究报告生成器 —— 自动从同花顺 iwencai + 东方财富 reportapi 双数据源拉取研报，AI 分析后生成单文件自包含 HTML 报告。

用户只需说出行业名称，AI 自动从研报中发现产业链环节并完成全部分析。

---

## 功能特性

- **双数据源平级采集**：同花顺 iwencai report-search（需 API Key）+ 东方财富 reportapi（免费公开）
- **自动发现环节**：AI 从研报标题和摘要中自动识别产业链细分环节
- **深度分析**：17 个模块覆盖核心判断、产业链结构、板块评分、标的池、约束条件、兑现进度等
- **单文件 HTML**：零外部依赖，CSS + JS 全部内联，浏览器直接打开
- **自动去重**：双源数据按 uid + 标题+日期联合去重，避免重复

## 数据源

| 数据源 | 认证 | 特点 |
|--------|------|------|
| **同花顺 iwencai report-search** | 需 `IWENCAI_API_KEY` | 按环节关键词精准搜索，带摘要 |
| **东方财富 reportapi** | 免费公开，无需 Key | 覆盖广、免费，按行业关键词过滤 |

两个数据源都可用时，同时拉取并合并去重；仅一个可用时自动降级。

## 快速开始

### 环境要求
- Python 3.8+
- 可选：`IWENCAI_API_KEY` 环境变量（如需使用同花顺数据源）

### 安装

```bash
# 克隆仓库
git clone https://github.com/weixue009-bot/industry-report-skill.git
cd industry-report-skill

# 安装依赖
pip install requests
```

### 使用

```bash
# 配置 API Key（可选）
export IWENCAI_API_KEY=your_api_key_here

# 采集研报数据
python scripts/collect_reports.py \
  --industry "创新药" \
  --segments "化学创新药,生物创新药,CXO,创新中药,原料药" \
  --months 3 \
  --size 10

# 生成 HTML 报告
python scripts/build_report.py \
  --data "analysis/创新药/analysis.json" \
  --output "output/创新药_产业研究报告.html"
```

## 项目结构

```
industry-report-skill/
├── SKILL.md                  # WorkBuddy/OpenClaw 技能定义
├── _meta.json                # 技能元数据
├── scripts/
│   ├── collect_reports.py    # 双数据源研报采集脚本
│   └── build_report.py       # HTML 报告生成脚本
├── templates/
│   └── report.html           # 单文件 HTML 报告模板
└── references/
    └── format.md             # 分析字段写作规范
```

## 参考与致谢

本项目的东财 reportapi 数据源接口参考了 [Simon 林](https://github.com/simonlin1212) 的 [a-stock-data](https://github.com/simonlin1212/a-stock-data) 项目。感谢 Simon 林对 A 股数据接口的整理与分享。

## License

MIT
