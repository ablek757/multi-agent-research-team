import json
import logging
from typing import Any, Callable, Dict, List

from agent.config import LLMConfig
from agent.llm import LLMClient

logger = logging.getLogger(__name__)


class BaseAgent:
    """Multi-Agent 研究团队的基础 Agent 类。

    提供统一的 LLM 调用、进度通知、JSON 解析回退等能力。
    具体角色通过覆写角色提示词和行为方法实现。
    """

    name: str = "base"

    def __init__(
        self,
        config: LLMConfig,
        progress_callback: Callable[[str], None] | None = None,
    ):
        self.config = config
        self.llm = LLMClient(config)
        self.progress_callback = progress_callback or (lambda msg: None)

    def _progress(self, message: str):
        logger.info("[%s] %s", self.name, message)
        self.progress_callback(f"[{self.name}] {message}")

    def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        """调用 LLM 完成一次对话。"""
        return self.llm._chat(system, user, json_mode)

    def parse_json(self, content: str, fallback: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON，失败时返回 fallback。"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("[%s] JSON 解析失败，使用 fallback", self.name)
            return fallback or {}

    def parse_json_list(
        self,
        content: str,
        key: str,
        count: int | None = None,
    ) -> List[str]:
        """从 JSON 对象中提取字符串列表。"""
        data = self.parse_json(content, {})
        items = data.get(key, [])
        if isinstance(items, list) and all(isinstance(x, str) for x in items):
            if count is not None:
                return items[:count]
            return items
        # Fallback: parse line by line
        lines = [line.strip("-• \t") for line in content.splitlines() if line.strip()]
        if count is not None:
            return lines[:count]
        return lines
