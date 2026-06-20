"""情报系统命令行入口。"""

import argparse
import logging
import sys
import time
from pathlib import Path

from agent.config import Config
from intelligence.scheduler import IntelligenceScheduler
from intelligence.service import IntelligenceService


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="实时研究情报系统：7×24 小时扫描全球学术源并推送简报。"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="手动执行一次扫描")
    scan_parser.add_argument(
        "--topic",
        action="append",
        help="指定扫描主题（可多次使用）",
    )

    daemon_parser = subparsers.add_parser("daemon", help="启动 7×24 守护进程")
    daemon_parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="扫描间隔小时数（覆盖配置）",
    )

    subparsers.add_parser("topics", help="列出当前监控主题")
    subparsers.add_parser("alerts", help="列出历史告警")
    subparsers.add_parser("briefings", help="列出历史简报")

    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)

    config = Config.load(args.config)
    config.validate()

    if args.command == "scan":
        service = IntelligenceService(config, progress_callback=print)
        service.run_scan(topics=args.topic)
    elif args.command == "daemon":
        if args.interval is not None:
            config.intelligence.scan_interval_hours = args.interval
        scheduler = IntelligenceScheduler(config)
        scheduler.start()
        print(
            f"情报守护进程已启动，每 {config.intelligence.scan_interval_hours} 小时扫描一次。"
            "按 Ctrl+C 停止。",
            flush=True,
        )
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            print("\n守护进程已停止。")
    elif args.command == "topics":
        service = IntelligenceService(config, progress_callback=print)
        topics = service.get_monitor_topics()
        if not topics:
            print("知识库为空，暂无监控主题。")
            return
        for topic, meta in topics.items():
            print(f"- {topic}")
            print(f"  实体: {', '.join(meta['entities'][:10])}")
            print(f"  报告数: {len(meta['report_ids'])}")
    elif args.command == "alerts":
        service = IntelligenceService(config)
        result = service.list_alerts(limit=50)
        print(f"共 {result['total']} 条告警：")
        for alert in result["alerts"]:
            a = alert["article"]
            s = alert["scores"]
            print(
                f"- [{alert['topic']}] {a['title']} "
                f"(R{s['relevance']} N{s['novelty']} B{s['breakthrough']})"
            )
    elif args.command == "briefings":
        service = IntelligenceService(config)
        result = service.list_briefings(limit=50)
        print(f"共 {result['total']} 份简报：")
        for briefing in result["briefings"]:
            print(f"- [{briefing['topic']}] {briefing['title']} ({briefing['date']})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断。", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logging.error("运行失败: %s", exc)
        sys.exit(1)
