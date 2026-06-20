"""用户研究风格学习器。"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from agent.config import StyleConfig
from agent.llm import LLMClient
from agent.style.models import UserStyleProfile

logger = logging.getLogger(__name__)


class StyleLearner:
    """从历史修订和反馈中学习用户研究风格。"""

    def __init__(self, config: StyleConfig, llm: Optional[LLMClient] = None):
        self.config = config
        self.llm = llm
        self.profile_path = Path(config.profile_path)
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)

    def load_profile(self) -> UserStyleProfile:
        """加载用户风格画像，若不存在则返回默认画像。"""
        if not self.profile_path.exists():
            return UserStyleProfile()
        try:
            data = json.loads(self.profile_path.read_text(encoding="utf-8"))
            return UserStyleProfile.from_storage(data)
        except Exception as exc:
            logger.warning("加载风格画像失败: %s", exc)
            return UserStyleProfile()

    def save_profile(self, profile: UserStyleProfile) -> None:
        """保存用户风格画像。"""
        self.profile_path.write_text(
            json.dumps(profile.to_storage(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def learn_from_edits(self, original: str, revised: str) -> UserStyleProfile:
        """从用户修订中学习风格差异。"""
        profile = self.load_profile()
        if not self.config.enabled:
            return profile

        profile.sample_count += 1

        # 简单规则：从修订中提取常用过渡词
        transitions = re.findall(r"(此外|然而|因此|综上所述|值得注意的是|另一方面|首先|其次|最后)", revised)
        for word in transitions:
            if word not in profile.transition_words:
                profile.transition_words.append(word)

        # 使用 LLM 进行更深层次的风格提取
        if self.llm is not None:
            try:
                diff_profile = self._analyze_style_difference(original, revised)
                profile = self._merge_profiles(profile, diff_profile)
            except Exception as exc:
                logger.warning("LLM 风格分析失败: %s", exc)

        self.save_profile(profile)
        return profile

    def learn_from_feedback(self, report_body: str, feedback: str) -> UserStyleProfile:
        """从编辑反馈中学习风格偏好。"""
        profile = self.load_profile()
        if not self.config.enabled:
            return profile

        profile.sample_count += 1

        if self.llm is not None:
            try:
                diff_profile = self._analyze_feedback(report_body, feedback)
                profile = self._merge_profiles(profile, diff_profile)
            except Exception as exc:
                logger.warning("LLM 反馈风格分析失败: %s", exc)

        self.save_profile(profile)
        return profile

    def _analyze_style_difference(self, original: str, revised: str) -> UserStyleProfile:
        """使用 LLM 分析 two texts 的风格差异。"""
        system = (
            "你是一位文本风格分析专家。请比较以下原文和修订文，提炼出修订者偏好的写作风格。\n"
            "输出严格为 JSON，字段包括：language, paragraph_length, citation_density, "
            "structure_preference, transition_words（列表）, critical_intensity（1-10）, tone, custom_notes。"
        )
        user = f"原文：\n{original[:4000]}\n\n修订文：\n{revised[:4000]}\n\n请输出风格画像 JSON。"
        content = self.llm.complete(system=system, user=user)
        return self._parse_profile(content)

    def _analyze_feedback(self, report_body: str, feedback: str) -> UserStyleProfile:
        """使用 LLM 从反馈中提取风格偏好。"""
        system = (
            "你是一位文本风格分析专家。请根据以下研究报告和审稿反馈，提炼出作者应遵循的写作风格。\n"
            "输出严格为 JSON，字段包括：language, paragraph_length, citation_density, "
            "structure_preference, transition_words（列表）, critical_intensity（1-10）, tone, custom_notes。"
        )
        user = f"报告：\n{report_body[:4000]}\n\n反馈：\n{feedback[:2000]}\n\n请输出风格画像 JSON。"
        content = self.llm.complete(system=system, user=user)
        return self._parse_profile(content)

    def _parse_profile(self, content: str) -> UserStyleProfile:
        content = content.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
        data = json.loads(content)
        return UserStyleProfile.from_storage(data)

    def _merge_profiles(
        self, existing: UserStyleProfile, new: UserStyleProfile
    ) -> UserStyleProfile:
        """将新学习到的风格合并入现有画像（简单加权）。"""
        n = max(existing.sample_count, 1)
        # 对连续值做简单移动平均
        existing.critical_intensity = int(
            round((existing.critical_intensity * (n - 1) + new.critical_intensity) / n)
        )

        # 合并过渡词
        for word in new.transition_words:
            if word not in existing.transition_words:
                existing.transition_words.append(word)

        # 当新样本明确指定离散属性时覆盖
        for field in ["language", "paragraph_length", "citation_density", "structure_preference", "tone"]:
            new_value = getattr(new, field)
            if new_value and new_value != getattr(existing, field):
                setattr(existing, field, new_value)

        if new.custom_notes:
            if existing.custom_notes:
                existing.custom_notes += "\n" + new.custom_notes
            else:
                existing.custom_notes = new.custom_notes

        return existing
