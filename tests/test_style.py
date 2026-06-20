"""用户研究风格学习测试。"""

import tempfile

from agent.config import StyleConfig
from agent.style import StyleLearner


def test_style_learner_load_save():
    with tempfile.TemporaryDirectory() as tmp:
        profile_path = f"{tmp}/profile.json"
        config = StyleConfig(enabled=True, profile_path=profile_path, min_samples=1)
        learner = StyleLearner(config)
        profile = learner.load_profile()
        assert profile.sample_count == 0

        updated = learner.learn_from_edits("原文", "修订文。此外，这是补充。")
        assert updated.sample_count == 1
        assert "此外" in updated.transition_words

        reloaded = learner.load_profile()
        assert reloaded.sample_count == 1
