# 自动化深度研究 Agent

输入一个研究主题，Agent 会自动搜索网络、阅读网页、迭代挖掘信息、发现跨来源关联，最终生成一份带引用的结构化 Markdown 深度研究报告。

## 核心能力

- **自动搜索**：根据主题生成多维度查询，使用 DuckDuckGo 免费搜索。
- **网页阅读**：抓取页面正文并去噪，使用 `trafilatura` + `BeautifulSoup` 双保险提取。
- **信息抽取**：借助 LLM 摘要每页内容，提取关键发现、实体、待解答问题。
- **迭代深化**：每轮结束后识别信息缺口，生成新的搜索查询继续探索。
- **关联发现**：综合多来源信息，提炼主题、关联、矛盾与剩余空白。
- **结构化报告**：生成包含执行摘要、背景、关键发现、关联分析、结论与参考来源的 Markdown 报告。

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
- `--depth`: 搜索迭代轮数
- `--output`: 报告输出路径
- `--config`: 配置文件路径
- `--verbose`: 显示详细日志

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
| `research.depth` | 迭代搜索轮数 |
| `research.queries_per_round` | 每轮生成的查询数 |
| `research.language` | 报告语言，`zh` 或 `en` |
| `report.title` | 报告标题 |

## 项目结构

```
deep-research-agent/
├── main.py                 # CLI 入口
├── config.yaml             # 默认配置
├── requirements.txt        # 依赖
├── README.md               # 本文件
├── test_smoke.py           # 无 LLM 的流水线冒烟测试
├── .env.example            # 环境变量示例
└── agent/
    ├── config.py           # 配置加载
    ├── search.py           # 搜索引擎封装
    ├── fetcher.py          # 网页抓取与正文提取
    ├── llm.py              # LLM 调用与提示词
    ├── research_state.py   # 研究状态管理
    ├── orchestrator.py     # 主研究循环
    └── report.py           # Markdown 报告生成
```

## 注意事项

- DuckDuckGo 搜索可能会因网络原因不稳定，可重试或检查网络。
- LLM API 调用会产生费用，请留意用量。
- 请遵守目标网站的 robots.txt 与使用条款，不要高频抓取。
- 在 Windows Git Bash 中若中文输出显示乱码，可设置 `export PYTHONIOENCODING=utf-8`。

## 许可证

MIT
