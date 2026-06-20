"""数据集摘要格式器：提取来源中的表格/数据线索，生成 CSV 摘要。"""

import csv
import re
from pathlib import Path
from typing import Dict, List

from agent.config import Config
from agent.output.base import OutputArtifact, OutputFormatter
from agent.research_state import ResearchState


class DatasetBriefFormatter(OutputFormatter):
    """生成数据来源与关键数据线索摘要 CSV。"""

    name = "dataset_brief"
    mime_type = "text/csv"
    extension = ".csv"

    def format(self, topic: str, state: ResearchState) -> OutputArtifact:
        rows: List[Dict[str, str]] = []
        max_rows = self.config.output.dataset_brief_max_rows

        # 从 sources 和 findings 中提取可能的数据线索
        for source in state.sources[:max_rows]:
            rows.append(
                {
                    "id": str(source.index),
                    "type": "source",
                    "title": source.title,
                    "url": source.url,
                    "value": source.snippet[:500],
                    "unit": "",
                    "notes": "",
                }
            )

        for i, finding in enumerate(state.findings[:max_rows], start=len(rows) + 1):
            numbers = self._extract_numbers(finding)
            rows.append(
                {
                    "id": f"f{i}",
                    "type": "finding",
                    "title": f"发现 #{i}",
                    "url": "",
                    "value": finding[:500],
                    "unit": "",
                    "notes": f"提取数字: {numbers}" if numbers else "",
                }
            )

        file_path = str(Path(self.config.report.output_dir) / f"{self._safe_name(topic)}_dataset.csv")
        Path(self.config.report.output_dir).mkdir(parents=True, exist_ok=True)

        fieldnames = ["id", "type", "title", "url", "value", "unit", "notes"]
        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        content = "\n".join(
            [",".join(fieldnames)]
            + [
                ",".join(f'"{str(row.get(k, "")).replace("\"", "\"\"")}"' for k in fieldnames)
                for row in rows
            ]
        )

        return OutputArtifact(
            format=self.name,
            content=content,
            file_path=file_path,
            mime_type=self.mime_type,
            metadata={"row_count": len(rows)},
        )

    def _extract_numbers(self, text: str) -> str:
        numbers = re.findall(r"\d+(?:\.\d+)?%?", text)
        return ", ".join(numbers[:5])

    def _safe_name(self, topic: str) -> str:
        return re.sub(r'[\\/:*?"<>|]+', "_", topic)[:50]
