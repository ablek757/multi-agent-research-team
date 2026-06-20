import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from agent.cognition import CognitiveController
from agent.config import Config
from agent.llm import LLMClient
from agent.orchestrator import ResearchOrchestrator
from agent.output import get_formatter
from agent.report import generate_report, save_report, save_state
from agent.style import StyleLearner
from kb import KnowledgeStore, parse_markdown_report


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="认知增强型 Multi-Agent 深度研究与创作系统：输入主题，自动生成结构化研究报告及多模态成果。"
    )
    parser.add_argument("topic", help="研究主题")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="搜索迭代轮数 (覆盖配置)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="报告输出路径 (默认: output/<主题>_<时间戳>.md)",
    )
    parser.add_argument(
        "--cognitive",
        action="store_true",
        help="启用认知增强控制层（任务分解、反思、重规划）",
    )
    parser.add_argument(
        "--formats",
        default=None,
        help="输出格式，逗号分隔。可选：markdown, slides, html, dataset_brief, action_plan",
    )
    parser.add_argument(
        "--style-profile",
        default=None,
        help="用户风格画像路径（覆盖配置中的 profile_path）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    config = Config.load(args.config)
    if args.depth is not None:
        config.research.depth = args.depth
    if args.cognitive:
        config.cognition.enabled = True
    if args.formats:
        config.output.formats = [f.strip() for f in args.formats.split(",")]
    if args.style_profile:
        config.style.enabled = True
        config.style.profile_path = args.style_profile
    config.validate()

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.topic)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config.report.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        output_path = args.output
    else:
        output_path = str(output_dir / f"{safe_name}_{timestamp}.md")

    def on_progress(message: str):
        print(f"[Agent] {message}", flush=True)

    kb_store = KnowledgeStore(
        data_dir=config.kb.data_dir,
        memory_config=config.memory,
        llm_config=config.llm,
    )

    style_profile = None
    if config.style.enabled:
        learner = StyleLearner(config.style)
        profile = learner.load_profile()
        if profile.sample_count >= config.style.min_samples:
            style_profile = profile

    llm_client = LLMClient(config.llm)

    if config.cognition.enabled:
        on_progress("[认知增强模式] 启动任务分解与动态规划")
        controller = CognitiveController(
            config=config,
            llm=llm_client,
            progress_callback=on_progress,
            kb_store=kb_store,
        )
        state = controller.run(args.topic)
    else:
        orchestrator = ResearchOrchestrator(config, progress_callback=on_progress)
        state = orchestrator.run(args.topic)

    print(f"\n共收集 {len(state.sources)} 个来源，{len(state.findings)} 条关键发现。")
    if state.metrics:
        print(f"综合质量评分: {state.metrics.get('overall_score', 'N/A')}")

    llm = llm_client

    # 生成多格式输出
    artifacts = []
    for fmt in config.output.formats:
        try:
            formatter = get_formatter(fmt, config, style_profile=style_profile)
            artifact = formatter.format(args.topic, state)
            artifacts.append(artifact)
            if artifact.file_path:
                print(f"✅ 已生成 {fmt}: {artifact.file_path}")
            else:
                # Markdown 默认写入 output_path
                if fmt == "markdown":
                    report = artifact.content
                    saved_path = save_report(report, output_path)
                    artifact.file_path = saved_path
                    print(f"✅ 研究报告已保存: {saved_path}")
        except Exception as exc:
            logging.warning("生成 %s 格式失败: %s", fmt, exc)

    # 兼容旧逻辑：默认 Markdown 输出
    if "markdown" not in config.output.formats:
        report = generate_report(
            topic=args.topic,
            state=state,
            config=config,
            llm=llm,
        )
        saved_path = save_report(report, output_path)
        print(f"✅ 研究报告已保存: {saved_path}")

    state_path = str(Path(output_path).with_suffix(".json"))
    save_state(state, state_path)
    print(f"✅ 研究状态已保存: {state_path}")

    if config.kb.auto_ingest:
        try:
            # 使用已初始化的 kb_store，避免重复加载
            markdown_artifact = next((a for a in artifacts if a.format == "markdown"), None)
            if markdown_artifact and markdown_artifact.file_path:
                md_path = markdown_artifact.file_path
            else:
                md_path = output_path
            ingested_report = parse_markdown_report(
                markdown_path=md_path,
                state_path=state_path,
            )
            kb_store.add_report(ingested_report)
            print(f"✅ 已导入知识库: {ingested_report.id}")
        except Exception as exc:
            logging.warning("自动导入知识库失败: %s", exc)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logging.error("运行失败: %s", exc)
        sys.exit(1)
