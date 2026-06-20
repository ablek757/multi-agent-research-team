import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from agent.config import Config
from agent.llm import LLMClient
from agent.orchestrator import ResearchOrchestrator
from agent.report import generate_report, save_report, save_state
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
        description="协作式 Multi-Agent 深度研究团队：输入主题，多 Agent 分工生成结构化研究报告。"
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
        help="报告输出路径 (默认: output/<主题>.md)",
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
    config.validate()

    output_path = args.output
    if not output_path:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.topic)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{config.report.output_dir}/{safe_name}_{timestamp}.md"

    def on_progress(message: str):
        print(f"[Agent] {message}", flush=True)

    orchestrator = ResearchOrchestrator(config, progress_callback=on_progress)
    state = orchestrator.run(args.topic)

    print(f"\n共收集 {len(state.sources)} 个来源，{len(state.findings)} 条关键发现。")

    llm = LLMClient(config.llm)
    report = generate_report(
        topic=args.topic,
        state=state,
        config=config,
        llm=llm,
    )

    saved_path = save_report(report, output_path)
    state_path = str(Path(output_path).with_suffix(".json"))
    save_state(state, state_path)
    print(f"\n✅ 研究报告已保存: {saved_path}")
    print(f"✅ 研究状态已保存: {state_path}")

    if getattr(config.kb, "auto_ingest", True):
        try:
            store = KnowledgeStore(data_dir=config.kb.data_dir)
            ingested_report = parse_markdown_report(
                markdown_path=saved_path,
                state_path=state_path,
            )
            store.add_report(ingested_report)
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
