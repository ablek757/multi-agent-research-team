import json
import logging
from typing import Dict, List, Optional

from openai import OpenAI

from agent.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        kwargs = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = OpenAI(**kwargs)

    def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        """通用对话完成接口。"""
        return self._chat(system, user, json_mode)

    def _chat(self, system: str, user: str, json_mode: bool = False) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                response_format={"type": "json_object"} if json_mode else None,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("LLM API call failed: %s", exc)
            raise

    def generate_search_queries(self, topic: str, count: int, language: str) -> List[str]:
        system = (
            "You are a research assistant. Given a research topic, generate diverse "
            "and specific search queries to gather comprehensive information. "
            "Return only a JSON object with a 'queries' key containing a list of strings."
        )
        lang_hint = "in Chinese" if language == "zh" else "in English"
        user = f"Topic: {topic}\nGenerate {count} search queries {lang_hint}."
        content = self._chat(system, user, json_mode=True)
        try:
            data = json.loads(content)
            queries = data.get("queries", [])
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return queries[:count]
        except json.JSONDecodeError:
            pass
        # Fallback: parse line by line
        return [line.strip("-• \t") for line in content.splitlines() if line.strip()][:count]

    def summarize_page(self, title: str, url: str, content: str, topic: str, language: str) -> Dict:
        system = (
            "You are an expert at extracting structured information from web pages. "
            "Read the provided page content and return a JSON object with these keys:\n"
            "- summary: a concise summary (2-4 sentences)\n"
            "- key_findings: a list of key factual claims or findings relevant to the topic\n"
            "- entities: a list of important people, organizations, technologies, or concepts mentioned\n"
            "- open_questions: a list of questions this page raises or leaves unanswered\n"
            "- relevance_score: integer 1-10 indicating how relevant the page is to the topic\n"
            "Return ONLY valid JSON."
        )
        lang_hint = "Respond in Chinese." if language == "zh" else "Respond in English."
        user = (
            f"Topic: {topic}\n"
            f"Page title: {title}\n"
            f"URL: {url}\n\n"
            f"Content:\n{content[:8000]}\n\n{lang_hint}"
        )
        content = self._chat(system, user, json_mode=True)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse summary JSON, returning raw text")
            return {
                "summary": content,
                "key_findings": [],
                "entities": [],
                "open_questions": [],
                "relevance_score": 5,
            }

    def identify_gaps(
        self,
        topic: str,
        findings: List[str],
        entities: List[str],
        open_questions: List[str],
        count: int,
        language: str,
    ) -> List[str]:
        system = (
            "You are a research strategist. Given what has been learned so far, "
            "identify the most important information gaps and return a JSON object "
            "with a 'queries' key containing follow-up search queries. "
            "Return ONLY valid JSON."
        )
        lang_hint = "Respond in Chinese." if language == "zh" else "Respond in English."
        user = (
            f"Topic: {topic}\n\n"
            f"Key findings so far:\n" + "\n".join(f"- {f}" for f in findings[-30:]) + "\n\n"
            f"Key entities: {', '.join(entities[-30:])}\n\n"
            f"Open questions:\n" + "\n".join(f"- {q}" for q in open_questions[-20:]) + "\n\n"
            f"Generate {count} follow-up search queries to fill the most important gaps. {lang_hint}"
        )
        content = self._chat(system, user, json_mode=True)
        try:
            data = json.loads(content)
            queries = data.get("queries", [])
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return queries[:count]
        except json.JSONDecodeError:
            pass
        return [line.strip("-• \t") for line in content.splitlines() if line.strip()][:count]

    def find_connections(
        self,
        topic: str,
        findings: List[str],
        entities: List[str],
        language: str,
    ) -> Dict:
        system = (
            "You are an analyst who discovers connections across sources. "
            "Given a set of findings and entities, identify themes, patterns, causal chains, "
            "and contradictions. Return a JSON object with:\n"
            "- themes: list of major themes\n"
            "- connections: list of connections between entities/findings\n"
            "- contradictions: list of any conflicting claims\n"
            "- gaps: list of remaining uncertainties\n"
            "Return ONLY valid JSON."
        )
        lang_hint = "Respond in Chinese." if language == "zh" else "Respond in English."
        user = (
            f"Topic: {topic}\n\n"
            f"Findings:\n" + "\n".join(f"- {f}" for f in findings[-50:]) + "\n\n"
            f"Entities: {', '.join(entities[-40:])}\n\n"
            f"Analyze connections and return structured JSON. {lang_hint}"
        )
        content = self._chat(system, user, json_mode=True)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "themes": [],
                "connections": [{"description": content}],
                "contradictions": [],
                "gaps": [],
            }

    def generate_report(
        self,
        topic: str,
        findings: List[str],
        entities: List[str],
        connections: Dict,
        sources: List[Dict],
        language: str,
    ) -> str:
        system = (
            "You are a senior research writer. Write a structured, in-depth research report "
            "in Markdown format. Use clear sections, bullet points, and paragraphs. "
            "Be factual and base all claims on the provided findings. "
            "Cite sources inline using [n] notation where n corresponds to the source index."
        )
        lang_hint = "Write in Chinese." if language == "zh" else "Write in English."
        sources_text = "\n".join(
            f"[{i}] {s['title']} - {s['url']}" for i, s in enumerate(sources, 1)
        )
        user = (
            f"Topic: {topic}\n\n"
            f"Findings:\n" + "\n".join(f"- {f}" for f in findings[-80:]) + "\n\n"
            f"Key entities: {', '.join(entities[-50:])}\n\n"
            f"Connection analysis:\n{json.dumps(connections, ensure_ascii=False, indent=2)}\n\n"
            f"Sources:\n{sources_text}\n\n"
            f"Write the report with these sections:\n"
            f"1. Executive Summary\n"
            f"2. Background / Context\n"
            f"3. Key Findings\n"
            f"4. Connections & Implications\n"
            f"5. Open Questions & Limitations\n"
            f"6. Conclusion\n\n"
            f"{lang_hint}"
        )
        return self._chat(system, user)
