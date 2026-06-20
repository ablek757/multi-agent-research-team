# 认知增强型研究执行与创作系统架构

## 1. 总体架构

本系统在原有 Multi-Agent 深度研究流水线之上，增加了一层**认知控制层（Cognitive Controller）**，并围绕它扩展了长期记忆、通用工具、多模态输出、风格学习与质量评估五大能力。

```text
用户输入主题
    │
    ▼
┌─────────────────────────────────────────┐
│      CognitiveController 认知控制器      │
│  · 加载相关历史研究（向量语义召回）        │
│  · TaskPlanner 分解子任务                │
│  · 循环执行子任务 → MetaCritic 反思       │
│  · 必要时重规划                          │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│       TeamOrchestrator 研究团队          │
│  SearchPlanner → Researcher → Analyst   │
│  → FactChecker → Writer → Editor        │
│  （ cognition.enabled 时加入 MetaCritic） │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│      OutputRegistry 多模态输出格式器      │
│  Markdown / PPT / HTML / CSV / ActionPlan│
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│      KnowledgeStore 知识库 + 向量记忆      │
│  JSONL + 倒排索引 + numpy embedding       │
└─────────────────────────────────────────┘
```

## 2. 认知控制层

### 2.1 组件

| 文件 | 类 | 职责 |
|------|-----|------|
| `agent/cognition/controller.py` | `CognitiveController` | 主控入口：加载记忆、分解任务、调度执行、反思、重规划、综合报告 |
| `agent/cognition/planner.py` | `TaskPlanner` | 将主题拆分为 `SubTask` 列表，支持根据反思结果重规划 |
| `agent/cognition/meta_critic.py` | `MetaCritic` | 对研究状态进行元认知反思，输出信息缺口、来源偏见、建议查询 |
| `agent/cognition/models.py` | `Plan` / `SubTask` / `Reflection` / `WorkingMemory` | 认知层数据模型 |

### 2.2 执行流程

1. **语义召回**：使用 `KnowledgeStore.semantic_search(topic)` 找到相关历史研究，作为上下文。
2. **任务分解**：`TaskPlanner.decompose()` 调用 LLM 生成 `SubTask[]`。
3. **子任务执行**：对每个就绪子任务，创建 `TeamOrchestrator` 并运行聚焦主题 `topic + subtask.goal`。
4. **状态合并**：将子任务结果合并入主 `ResearchState`。
5. **元认知反思**：`MetaCritic.reflect()` 分析当前状态，输出 `Reflection`。
6. **重规划**：若 `should_replan` 为 true 且未超过 `max_replan_iterations`，调整计划。
7. **综合输出**：使用 `Writer` 生成最终报告，可注入 `StyleProfile`。

## 3. 长期向量记忆

### 3.1 组件

| 文件 | 类 | 职责 |
|------|-----|------|
| `kb/embeddings.py` | `EmbeddingProvider` | embedding 抽象接口 |
| `kb/embeddings.py` | `OpenAIEmbeddingProvider` | OpenAI API embedding |
| `kb/embeddings.py` | `SentenceTransformerProvider` | 本地模型 embedding |
| `kb/embeddings.py` | `MockEmbeddingProvider` | 测试用确定性伪 embedding |
| `kb/embeddings.py` | `VectorMemory` | numpy 向量存储与余弦相似度检索 |
| `kb/store.py` | `KnowledgeStore` | 扩展 `embed_report` / `semantic_search` / `find_related_reports` |

### 3.2 存储格式

- 向量：`{vector_dir}/vectors.npy`
- 元数据：`{vector_dir}/metadata.jsonl`

每份报告生成一个 embedding，文本由标题、主题、发现、实体、主题拼接而成。

## 4. 通用工具注册表

### 4.1 组件

| 文件 | 类 | 职责 |
|------|-----|------|
| `agent/tools/base.py` | `BaseTool` / `ToolResult` | 工具抽象与结果模型 |
| `agent/tools/registry.py` | `ToolRegistry` | 注册、发现、调用工具 |
| `agent/tools/search_tool.py` | `SearchTool` | 网页搜索 |
| `agent/tools/fetch_tool.py` | `FetchTool` | 网页抓取 |
| `agent/tools/kb_tool.py` | `KBQueryTool` | 知识库查询 |
| `agent/tools/calculator_tool.py` | `CalculatorTool` | 安全数值计算 |
| `agent/tools/date_tool.py` | `DateTool` | 时间获取与解析 |

### 4.2 使用方式

```python
from agent.tools import build_default_registry
registry = build_default_registry(config=config)
registry.call("calculator", expression="(2 + 3) * 4")
```

## 5. 多模态创作输出

### 5.1 组件

| 文件 | 类 | 输出 |
|------|-----|------|
| `agent/output/markdown.py` | `MarkdownFormatter` | Markdown 报告 |
| `agent/output/slides.py` | `SlidesFormatter` | PPT（`.pptx`） |
| `agent/output/html.py` | `HTMLFormatter` | 单页 HTML 演示 |
| `agent/output/dataset_brief.py` | `DatasetBriefFormatter` | CSV 数据摘要 |
| `agent/output/action_plan.py` | `ActionPlanFormatter` | Markdown 可执行方案看板 |

### 5.2 扩展新格式

1. 继承 `OutputFormatter`。
2. 实现 `format(topic, state) -> OutputArtifact`。
3. 在 `agent/output/registry.py` 的 `FORMATTER_REGISTRY` 中注册。

## 6. 用户研究风格学习

### 6.1 组件

| 文件 | 类 | 职责 |
|------|-----|------|
| `agent/style/models.py` | `UserStyleProfile` | 风格画像模型 |
| `agent/style/learner.py` | `StyleLearner` | 从修订/反馈中学习并持久化 |

### 6.2 风格维度

- 语言（zh/en/mixed）
- 段落长度
- 引用密度
- 论述结构
- 语气
- 批判性强度
- 常用过渡词
- 自定义备注

### 6.3 触发方式

- CLI：`--style-profile path/to/profile.json`
- API：`POST /api/style/learn` 提交 `original+revised` 或 `original+feedback`
- 自动：当 `style.auto_learn_from_edits=true` 时，编辑审稿后会自动学习

## 7. 质量评估器

### 7.1 组件

| 文件 | 类 | 职责 |
|------|-----|------|
| `agent/evaluation/metrics.py` | `ReportMetrics` | 质量指标数据模型 |
| `agent/evaluation/metrics.py` | `ReportEvaluator` | 计算规则指标 + LLM 辅助评估 |

### 7.2 指标

| 指标 | 说明 |
|------|------|
| `source_count` | 来源数量 |
| `domain_diversity` | 来源域名多样性 |
| `citation_coverage` | 正文中引用标记覆盖的来源比例 |
| `claim_source_alignment` | 关键发现被正文提及的比例 |
| `length_score` | 报告长度得分 |
| `hallucination_risk` | 未引用数字声明占比估算 |
| `overall_score` | 加权综合得分 |

## 8. 配置说明

新增配置段落示例：

```yaml
cognition:
  enabled: false
  reflection_rounds: 1
  max_subtasks: 5
  enable_checkpoints: false
  max_replan_iterations: 2

memory:
  enabled: false
  backend: "openai"  # mock / sentence_transformers
  model: "text-embedding-3-small"
  vector_dir: "vectors"
  top_k: 10

output:
  formats:
    - "markdown"
    # - "slides"
    # - "html"
    # - "dataset_brief"
    # - "action_plan"

style:
  enabled: false
  profile_path: "data/user_style_profile.json"
  min_samples: 1
  auto_learn_from_edits: true
```

## 9. 扩展建议

1. **新增学术情报源**：继承 `intelligence/sources/base.py` 的 `AcademicSource`，注册到 `SOURCE_REGISTRY`。
2. **新增工具**：继承 `BaseTool`，在 `build_default_registry` 中注册。
3. **新增输出格式**：继承 `OutputFormatter`，在 `FORMATTER_REGISTRY` 中注册。
4. **替换 embedding 后端**：实现 `EmbeddingProvider`，在 `build_embedding_provider` 中注册。
