"""置信度评分：综合多源交叉验证信号，给出 0-100 分数与五级标签。"""

from typing import Dict

from .models import VerificationVerdict


class ConfidenceScorer:
    """基于交叉验证信号计算声明置信度。"""

    def score(self, signals: Dict) -> Dict:
        """返回 {'score': int, 'label': str, 'verdict': VerificationVerdict, 'concerns': list}。"""
        support = signals.get("supporting_count", 0)
        refute = signals.get("refuting_count", 0)
        domains = signals.get("unique_domain_count", 0)
        agreement = signals.get("agreement_ratio", 0.0)
        direct_quotes = signals.get("direct_quote_count", 0)
        relevance = signals.get("average_relevance", 0.0)

        # 各项子分数（0-1）
        source_score = min(1.0, support / 3.0)
        diversity_score = min(1.0, domains / 3.0)
        quote_score = min(1.0, direct_quotes / 2.0)
        relevance_score = relevance / 10.0

        # 综合分数（0-100）
        base_score = (
            source_score * 0.30
            + diversity_score * 0.20
            + agreement * 0.25
            + quote_score * 0.15
            + relevance_score * 0.10
        ) * 100

        concerns = []
        if support == 0 and refute == 0:
            concerns.append("未找到任何来源证据")
        if support == 1:
            concerns.append("仅单一来源支持")
        if domains <= 1 and support > 1:
            concerns.append("来源域名多样性不足")
        if direct_quotes == 0:
            concerns.append("缺少直接可溯源引用")
        if relevance_score < 0.4:
            concerns.append("证据与声明的相关性较弱")

        # 根据支持与反驳数量调整结论
        if refute > 0 and support == 0:
            # 有明确反驳且无支持证据
            score = int(base_score * 0.3)
            verdict = VerificationVerdict.REFUTED
            label = "被反驳"
            concerns.append("来源对声明提出反驳")
        elif refute >= support and refute >= 2:
            score = int(base_score * 0.3)
            verdict = VerificationVerdict.REFUTED
            label = "被反驳"
            concerns.append("多个来源对该声明提出反驳")
        elif refute > 0 and support > 0:
            score = int(base_score * 0.7)
            if score >= 60:
                score = min(score, 59)
            verdict = VerificationVerdict.CONTESTED
            label = "存在争议"
            concerns.append("来源之间存在分歧")
        elif support == 0:
            score = int(base_score)
            verdict = VerificationVerdict.UNSUPPORTED
            label = "未证实"
        else:
            score = int(base_score)
            if score >= 80:
                verdict = VerificationVerdict.VERIFIED
                label = "已验证"
            elif score >= 60:
                verdict = VerificationVerdict.PLAUSIBLE
                label = "较可信"
            else:
                verdict = VerificationVerdict.UNSUPPORTED
                label = "未证实"

        # 分数边界保护
        score = max(0, min(100, score))

        return {
            "score": score,
            "label": label,
            "verdict": verdict,
            "concerns": concerns,
        }
