"""用户研究风格模型。"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserStyleProfile(BaseModel):
    """用户研究风格画像。"""

    language: str = "zh"  # zh / en / mixed
    paragraph_length: str = "medium"  # short / medium / long
    citation_density: str = "medium"  # low / medium / high
    structure_preference: str = "standard"  # standard / narrative / bullet_heavy
    transition_words: List[str] = Field(default_factory=list)
    critical_intensity: int = 5  # 1-10，批判性强度
    tone: str = "neutral"  # neutral / formal / conversational
    custom_notes: str = ""
    sample_count: int = 0

    def to_prompt_instructions(self) -> str:
        """将风格画像转换为可嵌入 system prompt 的指令文本。"""
        lines = [
            "请严格遵循以下用户研究风格偏好：",
            f"- 主要语言：{self.language}",
            f"- 段落长度：{self.paragraph_length}",
            f"- 引用密度：{self.citation_density}",
            f"- 论述结构：{self.structure_preference}",
            f"- 语气：{self.tone}",
            f"- 批判性强度（1-10）：{self.critical_intensity}",
        ]
        if self.transition_words:
            lines.append(f"- 偏好的过渡词：{', '.join(self.transition_words)}")
        if self.custom_notes:
            lines.append(f"- 其他偏好：{self.custom_notes}")
        return "\n".join(lines)

    def to_storage(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_storage(cls, data: Dict[str, Any]) -> "UserStyleProfile":
        return cls(**data)
