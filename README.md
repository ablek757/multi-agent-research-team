# 协作式 Multi-Agent 深度研究团队

输入一个研究主题，由多个专业 Agent 组成的协作团队自动完成搜索、研究、分析、核查、撰稿与审稿，最终生成一份带引用的结构化 Markdown 深度研究报告。

## 核心能力

- **多 Agent 协作**：SearchPlanner、Researcher、Analyst、FactChecker、Writer、Editor 六大角色分工协作，模拟人类研究团队。
- **自动搜索**：根据主题和当前缺口生成多维度查询，使用 DuckDuckGo 免费搜索。
- **网页阅读**：抓取页面正文并去噪，使用 `trafilatura` + `BeautifulSoup` 双保险提取。
- **信息抽取**：Researcher 借助 LLM 摘要每页内容，提取关键发现、实体、待解答问题。
- **深度分析**：Analyst 综合多来源信息，提炼主题、关联、矛盾与剩余空白。
- **事实核查**：FactChecker 对关键发现进行来源交叉验证、可信度评分与风险标记。
- **迭代优化**：若发现信息缺口或低可信度结论，自动触发补充搜索，循环深化。
- **撰稿与审稿**：Writer 生成结构化报告，Editor 审核并提出修改意见，Writer 再修订。
- **结构化报告**：生成包含执行摘要、背景、关键发现、关联分析、核查结论、局限性与参考来源的 Markdown 报告。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 LLM

复制或编辑 `config.yaml`，填入你的 API Key，或设置环境变量：

```bash
export OPENAI_API_KEY="sk-xxx"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选，兼容 OpenAI 接口的第三方服务
export OPENAI_MODEL="gpt-4o-mini"                   # 可选，覆盖 config.yaml 中的模型
```

### 3. 运行

```bash
python main.py "量子计算在药物发现中的应用"
```

更多选项：

```bash
python main.py "人工智能对齐研究现状" --depth 3 --output output/report.md --verbose
```

### 4. 快速验证（无需真实 LLM）

```bash
python test_smoke.py
```

参数说明：
- `--topic`: 研究主题（必填）
- `--depth`: 搜索迭代轮数（覆盖 `research.depth`，`team.max_research_iterations` 为 0 时生效）
- `--output`: 报告输出路径
- `--config`: 配置文件路径
- `--verbose`: 显示详细日志

## Agent 角色与协作流程

```
SearchPlanner → Researcher → Analyst → FactChecker
                     ↑___________________________↓
                          （缺口/低可信度则再迭代）
                                   ↓
                    Writer → Editor → Writer（修订）→ 最终报告
```

| 角色 | 职责 |
|------|------|
| **SearchPlanner** | 根据主题和当前研究缺口生成搜索查询 |
| **Researcher** | 执行搜索、抓取网页、提取关键发现、实体与待解答问题 |
| **Analyst** | 跨来源综合，提炼主题、关联、矛盾与剩余缺口 |
| **FactChecker** | 对关键发现进行交叉验证、可信度评分、偏见/风险标记 |
| **Writer** | 基于验证后的材料撰写结构化、带引用的 Markdown 报告 |
| **Editor** | 审核报告质量，指出逻辑漏洞与信息缺口，提出修改意见 |

## 配置说明

`config.yaml` 中可调参数：

| 配置项 | 说明 |
|--------|------|
| `llm.model` | 使用的 LLM 模型 |
| `llm.temperature` | 生成温度 |
| `llm.max_tokens` | 单次最大 token 数 |
| `search.results_per_query` | 每个查询返回的搜索结果数 |
| `search.top_k_to_fetch` | 每个查询实际抓取的页面数 |
| `search.max_workers` | 并发抓取线程数 |
| `research.depth` | 默认研究迭代轮数 |
| `research.queries_per_round` | 每轮生成的查询数 |
| `research.language` | 报告语言，`zh` 或 `en` |
| `report.title` | 报告标题 |
| `team.enable_fact_checker` | 是否启用事实核查员 |
| `team.enable_editor` | 是否启用编辑审核员 |
| `team.max_research_iterations` | 研究阶段最大迭代轮数；`0` 表示使用 `research.depth` |
| `team.review_rounds` | 编辑审稿-修订轮数 |
| `team.min_credibility_threshold` | 触发补充搜索的可信度阈值（1-10） |
| `team.max_claims_to_verify` | 每轮核查的最大声明数 |

## 项目结构

```
deep-research-agent/
├── main.py                 # CLI 入口
├── config.yaml             # 默认配置
├── requirements.txt        # 依赖
├── README.md               # 本文件
├── test_smoke.py           # 无 LLM 的多 Agent 流水线冒烟测试
├── .env.example            # 环境变量示例
└── agent/
    ├── agents/             # 多 Agent 角色
    │   ├── base.py
    │   ├── search_planner.py
    │   ├── researcher.py
    │   ├── analyst.py
    │   ├── fact_checker.py
    │   ├── writer.py
    │   └── editor.py
    ├── config.py           # 配置加载
    ├── search.py           # 搜索引擎封装
    ├── fetcher.py          # 网页抓取与正文提取
    ├── llm.py              # LLM 调用
    ├── research_state.py   # 研究状态管理
    ├── orchestrator.py     # 多 Agent 团队协调器
    └── report.py           # Markdown 报告生成
```

## 注意事项

- DuckDuckGo 搜索可能会因网络原因不稳定，可重试或检查网络。
- LLM API 调用会产生费用，请留意用量；可通过 `team` 配置关闭 FactChecker/Editor 以降低成本。
- 请遵守目标网站的 robots.txt 与使用条款，不要高频抓取。
- 在 Windows Git Bash 中若中文输出显示乱码，可设置 `export PYTHONIOENCODING=utf-8`。

## 许可证

MIT
