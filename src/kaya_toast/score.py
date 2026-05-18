from __future__ import annotations

from kaya_toast.config import load_scoring
from kaya_toast.fluff import OPERATIONAL_WORDS, fluff_check
from kaya_toast.models import Article, ClassificationResult, ScoreResult


PM_TERMS = ["pm", "product", "product manager", "product management", "roadmap"]
AI_NATIVE_TERMS = [
    "ai-native",
    "ai pm",
    "agent",
    "context",
    "prototyping",
    "llm",
    "human in the loop",
]
TRANSITION_TERMS = ["traditional pm", "transition", "upskill", "career", "pm role"]
ENTERPRISE_TERMS = [
    "enterprise",
    "governance",
    "operating model",
    "workflow",
    "risk",
    "audit",
    "compliance",
    "banking",
]
LINKEDIN_TERMS = ["misconception", "lesson", "why", "how", "shift", "playbook"]
ORIGINALITY_TERMS = [
    "decision loop",
    "context layer",
    "orchestration",
    "operating model",
    "human in the loop",
]
GENERIC_HYPE_TERMS = ["ai revolution", "game changer", "unlock productivity", "future-proof"]


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def score_article(
    article: Article,
    classification: ClassificationResult | None = None,
    scoring_config: dict | None = None,
) -> ScoreResult:
    config = scoring_config or load_scoring()
    weights = config["weights"]
    penalty_weights = config["penalties"]
    thresholds = config["thresholds"]
    text = f"{article.title} {article.summary}".lower()
    fluff = fluff_check(article)

    positive_scores = {
        "ai_native_pm_relevance": weights["ai_native_pm_relevance"]
        if _has_any(text, AI_NATIVE_TERMS) and _has_any(text, PM_TERMS)
        else 0,
        "pm_transition_value": weights["pm_transition_value"]
        if _has_any(text, TRANSITION_TERMS) or "ai pm" in text
        else 0,
        "practical_usefulness": weights["practical_usefulness"]
        if _has_any(text, OPERATIONAL_WORDS)
        else 0,
        "enterprise_relevance": weights["enterprise_relevance"]
        if _has_any(text, ENTERPRISE_TERMS)
        else 0,
        "linkedin_potential": weights["linkedin_potential"]
        if _has_any(text, LINKEDIN_TERMS) or (classification and classification.confidence >= 0.67)
        else 0,
        "originality": weights["originality"] if _has_any(text, ORIGINALITY_TERMS) else 0,
    }

    penalties: dict[str, int] = {}
    if fluff.fluff_score >= 50:
        penalties["fluff_risk"] = penalty_weights["fluff_risk"]
    if _has_any(text, GENERIC_HYPE_TERMS):
        penalties["generic_ai_hype"] = penalty_weights["generic_ai_hype"]
    if not _has_any(text, PM_TERMS):
        penalties["no_pm_relevance"] = penalty_weights["no_pm_relevance"]
    if not _has_any(text, OPERATIONAL_WORDS):
        penalties["no_operational_detail"] = penalty_weights["no_operational_detail"]

    total_score = max(0, sum(positive_scores.values()) + sum(penalties.values()))
    if total_score >= thresholds["post"]:
        recommendation = "post"
    elif total_score >= thresholds["park"]:
        recommendation = "park"
    else:
        recommendation = "reject"

    return ScoreResult(
        total_score=total_score,
        positive_scores=positive_scores,
        penalties=penalties,
        recommendation=recommendation,
    )
