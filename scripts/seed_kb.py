"""生成示例研究数据并导入知识库，用于演示。"""

import json
from pathlib import Path

from kb import KnowledgeStore, parse_research_state


def main():
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    sample_states = [
        {
            "title": "人工智能在医疗诊断中的应用",
            "topic": "AI 医疗诊断",
            "content": """
# 人工智能在医疗诊断中的应用

**研究主题**: 人工智能在医疗诊断中的应用
**生成时间**: 2024-06-15 10:00:00
**模型**: gpt-4o-mini

---

## 执行摘要

人工智能（AI）在医疗诊断领域的应用正在快速发展。2023年，多个深度学习模型在影像诊断中超越了人类专家水平。2024年6月，FDA 批准了多款 AI 辅助诊断工具。

## 关键发现

- 深度学习在放射影像诊断中的准确率持续提升。
- 自然语言处理技术被用于电子病历分析和临床决策支持。
- 2024年，多模态大模型开始整合影像、文本与基因组数据。

## 关联分析

AI 医疗诊断与医学影像、自然语言处理、临床决策支持系统密切相关。Google DeepMind、OpenAI 和多家医院正在推动该领域发展。

## 参考来源

[1] [Nature Medicine](https://example.com/nature-medicine)
[2] [FDA AI 审批公告](https://example.com/fda)
""",
            "sources": [
                {"index": 1, "title": "Nature Medicine", "url": "https://example.com/nature-medicine", "snippet": ""},
                {"index": 2, "title": "FDA AI 审批公告", "url": "https://example.com/fda", "snippet": ""},
            ],
            "summaries": [
                {
                    "source_index": 1,
                    "url": "https://example.com/nature-medicine",
                    "title": "Nature Medicine",
                    "summary": "AI in medical diagnosis",
                    "key_findings": ["深度学习在影像诊断中超越人类专家", "多模态模型整合多种数据类型"],
                    "entities": ["深度学习", "医学影像", "自然语言处理", "临床决策支持", "Google DeepMind", "OpenAI"],
                    "open_questions": [],
                    "relevance_score": 9,
                },
                {
                    "source_index": 2,
                    "url": "https://example.com/fda",
                    "title": "FDA AI 审批公告",
                    "summary": "FDA approved AI tools",
                    "key_findings": ["FDA 批准多款 AI 辅助诊断工具"],
                    "entities": ["FDA", "AI 辅助诊断", "临床决策支持"],
                    "open_questions": [],
                    "relevance_score": 8,
                },
            ],
            "findings": ["深度学习在影像诊断中超越人类专家", "多模态模型整合多种数据类型", "FDA 批准多款 AI 辅助诊断工具"],
            "entities": ["深度学习", "医学影像", "自然语言处理", "临床决策支持", "Google DeepMind", "OpenAI", "FDA", "AI 辅助诊断"],
            "themes": ["人工智能", "医疗诊断", "深度学习"],
        },
        {
            "title": "量子计算在药物发现中的应用",
            "topic": "量子计算 药物发现",
            "content": """
# 量子计算在药物发现中的应用

**研究主题**: 量子计算在药物发现中的应用
**生成时间**: 2024-08-20 14:00:00
**模型**: gpt-4o-mini

---

## 执行摘要

量子计算为药物发现中的分子模拟提供了新的可能性。2022年，IBM 发布了首批用于药物研发的量子计算试点项目。2024年，Google Quantum AI 在蛋白质折叠模拟中取得突破。

## 关键发现

- 量子计算可加速分子相互作用模拟。
- 2023年，多家制药公司开始与量子计算公司合作。
- 量子机器学习成为新的研究热点。

## 关联分析

量子计算与人工智能、药物化学、蛋白质折叠、机器学习密切相关。IBM、Google、辉瑞等公司处于领先地位。

## 参考来源

[1] [IBM Quantum](https://example.com/ibm-quantum)
[2] [Google Quantum AI](https://example.com/google-quantum)
""",
            "sources": [
                {"index": 1, "title": "IBM Quantum", "url": "https://example.com/ibm-quantum", "snippet": ""},
                {"index": 2, "title": "Google Quantum AI", "url": "https://example.com/google-quantum", "snippet": ""},
            ],
            "summaries": [
                {
                    "source_index": 1,
                    "url": "https://example.com/ibm-quantum",
                    "title": "IBM Quantum",
                    "summary": "Quantum computing for drug discovery",
                    "key_findings": ["IBM 发布药物研发量子计算试点", "量子计算加速分子模拟"],
                    "entities": ["量子计算", "IBM", "药物发现", "分子模拟"],
                    "open_questions": [],
                    "relevance_score": 9,
                },
                {
                    "source_index": 2,
                    "url": "https://example.com/google-quantum",
                    "title": "Google Quantum AI",
                    "summary": "Protein folding simulation",
                    "key_findings": ["Google 在蛋白质折叠模拟中取得突破", "量子机器学习成为热点"],
                    "entities": ["Google", "蛋白质折叠", "量子机器学习", "人工智能"],
                    "open_questions": [],
                    "relevance_score": 8,
                },
            ],
            "findings": ["IBM 发布药物研发量子计算试点", "量子计算加速分子模拟", "Google 在蛋白质折叠模拟中取得突破", "量子机器学习成为热点"],
            "entities": ["量子计算", "IBM", "药物发现", "分子模拟", "Google", "蛋白质折叠", "量子机器学习", "人工智能"],
            "themes": ["量子计算", "药物发现", "机器学习"],
        },
    ]

    store = KnowledgeStore(data_dir="data")

    for idx, sample in enumerate(sample_states, 1):
        md_path = output_dir / f"sample_report_{idx}.md"
        md_path.write_text(sample["content"], encoding="utf-8")

        state = {
            "sources": sample["sources"],
            "summaries": sample["summaries"],
            "findings": sample["findings"],
            "entities": sample["entities"],
            "open_questions": [],
            "themes": sample["themes"],
            "connections": [],
            "contradictions": [],
            "gaps": [],
            "verification_results": [],
            "editor_feedback": [],
            "revisions": [],
        }
        json_path = output_dir / f"sample_report_{idx}.json"
        json_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        report = parse_research_state(
            state=state,
            title=sample["title"],
            topic=sample["topic"],
            content=sample["content"],
            markdown_path=str(md_path.resolve()),
            state_path=str(json_path.resolve()),
        )
        store.add_report(report)
        print(f"已导入示例报告: {report.title} ({report.id})")

    stats = store.get_stats()
    print(f"\n知识库统计: {stats}")


if __name__ == "__main__":
    main()
