# 认知增强型研究执行与创作系统

输入一个研究主题，系统自动完成主题分解、多 Agent 协作研究、元认知反思、知识库持久化，并一键输出 Markdown 报告、PPT、HTML 演示、数据集摘要与可执行方案看板等多种模态成果。系统持续学习用户的研究风格，让后续输出越来越贴合个人偏好。

## 核心能力

- **认知增强控制层**：将复杂主题自动拆分为子任务，动态规划、执行、反思，必要时重规划。
- **多 Agent 协作**：SearchPlanner、Researcher、Analyst、FactChecker、Writer、Editor 六大角色分工协作，模拟人类研究团队。
- **元认知反思**：MetaCritic 在研究过程中主动发现信息缺口、来源偏见与计划偏差，并推荐下一轮查询。
- **通用工具注册表**：搜索、网页抓取、知识库查询、计算、日期解析等能力统一封装为可插拔工具。
- **长期向量记忆**：基于 embedding 的语义记忆，支持跨研究召回相关报告，发现隐藏关联。
- **自动搜索**：根据主题和当前缺口生成多维度查询，使用 DuckDuckGo 免费搜索。
- **网页阅读**：抓取页面正文并去噪，使用 `trafilatura` + `BeautifulSoup` 双保险提取。
- **信息抽取**：Researcher 借助 LLM 摘要每页内容，提取关键发现、实体、待解答问题。
- **深度分析**：Analyst 综合多来源信息，提炼主题、关联、矛盾与剩余空白。
- **事实核查**：FactChecker 对关键发现进行来源交叉验证、可信度评分与风险标记。
- **迭代优化**：若发现信息缺口或低可信度结论，自动触发补充搜索，循环深化。
- **撰稿与审稿**：Writer 生成结构化报告，Editor 审核并提出修改意见，Writer 再修订。
- **多模态创作输出**：一次研究可生成 Markdown、PPT（`python-pptx`）、HTML 演示页、数据集摘要 CSV、可执行方案看板。
- **用户研究风格学习**：从历史修订与审稿反馈中提取语言、段落长度、引用密度、语气等偏好，后续自动应用。
- **质量评估器**：自动评估来源多样性、引用覆盖率、声明-来源对齐度、篇幅完整性与幻觉风险，输出综合评分。
- **知识库存储**：自动生成与 Markdown 配套的结构化 JSON state，并导入知识库持久化。
- **主题关联分析**：基于实体共现构建交互式力导向关联网络。
- **时间线追踪**：自动从报告中抽取时间表达式与关键事件，生成研究时间线。
- **可检索前端**：提供 Next.js 可视化界面，支持认知研究、语义记忆检索、风格学习、报告浏览、关联图与时间线。
- **实时研究情报**：7×24 小时自动扫描 arXiv、PubMed、bioRxiv、Semantic Scholar、OpenAlex，基于知识库主题发现新突破，生成个性化简报并主动推送。

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

启用认知增强并生成多模态成果：

```bash
python main.py "量子计算在药物发现中的应用" \
  --cognitive \
  --formats markdown,slides,html,dataset_brief,action_plan \
  --verbose
```

更多选项：

```bash
python main.py "人工智能对齐研究现状" --depth 3 --output output/report.md --verbose
```

### 4. 启动知识库与可视化前端

```bash
# 启动 FastAPI 后端（默认 http://localhost:8000）
python api.py

# 新终端：启动 Next.js 前端（默认 http://localhost:3000）
cd web
npm run dev
```

### 5. 启动实时研究情报系统（可选）

```bash
# 方式一：启动 API 服务，自动后台 7×24 小时扫描
python api.py

# 方式二：手动执行一次扫描
python -m intelligence.cli scan

# 方式三：启动独立守护进程
python -m intelligence.cli daemon
```

扫描结果会生成告警与简报，自动导入知识库，并可通过邮件/Webhook 推送。

### 6. 快速验证（无需真实 LLM）

```bash
python test_smoke.py

# 导入示例数据体验知识库
PYTHONPATH=. python scripts/seed_kb.py
```

参数说明：
- `topic`: 研究主题（必填）
- `--depth`: 搜索迭代轮数（覆盖 `research.depth`，`team.max_research_iterations` 为 0 时生效）
- `--output`: 报告输出路径
- `--config`: 配置文件路径
- `--cognitive`: 启用认知增强控制层
- `--formats`: 输出格式，逗号分隔：`markdown` / `slides` / `html` / `dataset_brief` / `action_plan`
- `--style-profile`: 用户风格画像路径
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
| `kb.data_dir` | 知识库数据目录 |
| `kb.auto_ingest` | 生成报告后是否自动导入知识库 |
| `intelligence.enabled` | 是否启用实时情报系统 |
| `intelligence.scan_interval_hours` | 扫描间隔（小时） |
| `intelligence.lookback_days` | 每次扫描回看天数 |
| `intelligence.sources` | 启用的学术源列表 |
| `intelligence.thresholds.*` | 相关性/新颖性/突破性阈值（1-10） |
| `intelligence.notify.channels` | 推送渠道：`console` / `email` / `webhook` |
| `intelligence.notify.email.*` | SMTP 邮件配置 |
| `intelligence.notify.webhook.url` | Webhook 地址 |
| `cognition.enabled` | 是否启用认知增强控制层 |
| `cognition.reflection_rounds` | 每轮研究后的反思次数 |
| `cognition.max_subtasks` | 主题最大子任务数 |
| `cognition.enable_checkpoints` | 是否在关键节点暂停等待人工确认 |
| `cognition.max_replan_iterations` | 单次研究最大重规划次数 |
| `memory.enabled` | 是否启用向量长期记忆 |
| `memory.backend` | embedding 后端：`openai` / `sentence_transformers` / `mock` |
| `memory.model` | embedding 模型名 |
| `memory.vector_dir` | 向量存储目录 |
| `memory.top_k` | 语义检索返回数量 |
| `output.formats` | 默认输出格式列表 |
| `output.slides_template` | PPT 模板标识 |
| `output.html_theme` | HTML 主题标识 |
| `style.enabled` | 是否启用用户研究风格学习 |
| `style.profile_path` | 风格画像文件路径 |
| `style.min_samples` | 触发风格学习的最小样本数 |

## 知识库 API

后端启动后访问 http://localhost:8000/docs 查看自动生成的 API 文档。主要接口：

| 接口 | 说明 |
|------|------|
| `GET /api/stats` | 仪表盘统计 |
| `GET /api/reports` | 报告列表与搜索 |
| `GET /api/reports/{id}` | 报告详情 |
| `GET /api/reports/{id}/related` | 相关历史报告（向量召回） |
| `GET /api/search?q=...` | 全文检索 |
| `POST /api/memory/search` | 语义记忆检索 |
| `GET /api/graph` | 主题关联图数据 |
| `GET /api/timeline` | 跨报告时间线 |
| `POST /api/reports/ingest` | 批量导入报告目录 |
| `GET /api/formats` | 列出支持的输出格式 |
| `POST /api/research` | 启动研究任务（后台执行） |
| `GET /api/research/{job_id}` | 查询研究任务状态 |
| `GET /api/style/profile` | 获取用户风格画像 |
| `POST /api/style/learn` | 提交样本学习风格 |
| `POST /api/output/{format}` | 将已有 Markdown 转换为指定格式 |
| `GET /api/intelligence/topics` | 当前监控主题与实体 |
| `GET /api/intelligence/alerts` | 情报告警列表 |
| `GET /api/intelligence/briefings` | 研究简报列表 |
| `POST /api/intelligence/run` | 手动触发一次扫描 |

## 项目结构

```
deep-research-agent/
├── main.py                 # CLI 入口
├── api.py                  # FastAPI 知识库服务
├── config.yaml             # 默认配置
├── requirements.txt        # 依赖
├── README.md               # 本文件
├── test_smoke.py           # 无 LLM 的多 Agent 流水线冒烟测试
├── .env.example            # 环境变量示例
├── data/                   # 知识库持久化数据
├── output/                 # 生成的 Markdown 报告与 JSON state
├── scripts/                # 辅助脚本
│   └── seed_kb.py          # 示例数据导入
├── kb/                     # 知识库核心模块
│   ├── models.py           # 数据模型
│   ├── parser.py           # 报告解析器
│   ├── store.py            # 存储与索引
│   ├── analyzer.py         # 主题关联分析
│   ├── timeline.py         # 时间线抽取
│   └── search.py           # 全文检索
├── web/                    # Next.js 可视化前端
│   ├── app/                # 页面路由
│   ├── components/         # 可复用组件
│   └── lib/api.ts          # API 客户端
└── agent/                  # 多 Agent 研究团队
    ├── agents/             # 多 Agent 角色
    │   ├── base.py
    │   ├── search_planner.py
    │   ├── researcher.py
    │   ├── analyst.py
    │   ├── fact_checker.py
    │   ├── writer.py
    │   └── editor.py
    ├── cognition/          # 认知增强控制层
    │   ├── controller.py
    │   ├── planner.py
    │   ├── meta_critic.py
    │   └── models.py
    ├── tools/              # 通用工具注册表
    │   ├── base.py
    │   ├── registry.py
    │   ├── search_tool.py
    │   ├── fetch_tool.py
    │   ├── kb_tool.py
    │   ├── calculator_tool.py
    │   └── date_tool.py
    ├── output/             # 多模态创作输出格式器
    │   ├── base.py
    │   ├── registry.py
    │   ├── markdown.py
    │   ├── slides.py
    │   ├── html.py
    │   ├── dataset_brief.py
    │   └── action_plan.py
    ├── style/              # 用户研究风格学习
    │   ├── models.py
    │   └── learner.py
    ├── evaluation/         # 报告质量评估
    │   └── metrics.py
    ├── config.py           # 配置加载
    ├── search.py           # 搜索引擎封装
    ├── fetcher.py          # 网页抓取与正文提取
    ├── llm.py              # LLM 调用
    ├── research_state.py   # 研究状态管理
    ├── orchestrator.py     # 多 Agent 团队协调器
    └── report.py           # Markdown 报告生成
├── intelligence/           # 实时研究情报系统
    ├── sources/            # 学术源适配器（arXiv/PubMed/bioRxiv/S2/OpenAlex）
    ├── models.py           # 文章、告警、简报模型
    ├── store.py            # 情报本地存储
    ├── matcher.py          # 主题匹配与 LLM 评分
    ├── briefing.py         # 简报生成器
    ├── notifier.py         # 邮件/Webhook 推送
    ├── scheduler.py        # 7×24 小时调度器
    ├── service.py          # 情报服务主类
    └── cli.py              # 命令行入口
```

## 注意事项

- DuckDuckGo 搜索可能会因网络原因不稳定，可重试或检查网络。
- LLM API 调用会产生费用，请留意用量；可通过 `team` 配置关闭 FactChecker/Editor 以降低成本。
- 请遵守目标网站的 robots.txt 与使用条款，不要高频抓取。
- 在 Windows Git Bash 中若中文输出显示乱码，可设置 `export PYTHONIOENCODING=utf-8`。

## 许可证

MIT
