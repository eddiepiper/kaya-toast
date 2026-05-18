from __future__ import annotations

from kaya_toast.fluff import fluff_check
from kaya_toast.memory import score_positioning
from kaya_toast.models import Article, ClassificationResult, ContentIdea, ScoreResult
from kaya_toast.pillars import classify_pillar
from kaya_toast.preference import calculate_preference_adjustment
from kaya_toast.quality import assess_title_quality, assess_topic_quality


CATEGORY_ANGLES = {
    "ai_native_pm_mindset": "Challenge the misconception that AI-native PM is only about productivity.",
    "ai_pm_skills": "Show which PM skills compound when AI becomes part of the operating model.",
    "ai_workflow_redesign": "Frame AI-native PM as workflow redesign, not tool adoption.",
    "agentic_workflows": "Explain where agentic workflows need PM-designed guardrails and review loops.",
    "ai_prototyping": "Position prototyping as a faster way to test product judgment, not just UI output.",
    "context_engineering": "Make context engineering concrete for PM decisions, memory, and retrieval.",
    "human_in_loop_systems": "Show why human review and escalation are product design choices.",
    "ai_governance": "Translate AI governance into practical product operating discipline.",
    "product_discovery_with_ai": "Show how AI changes discovery loops without replacing customer evidence.",
    "traditional_pm_to_ai_pm": "Help traditional PMs see the operating shift required for AI PM roles.",
    "enterprise_ai_operating_models": "Connect enterprise AI strategy to PM workflow and decision design.",
}


def build_content_idea(
    article: Article,
    classification: ClassificationResult,
    score: ScoreResult,
) -> ContentIdea:
    topic = _topic_for(article, classification.category)
    fluff = fluff_check(article)
    idea_id = _idea_id_for(classification.category, topic)
    base_idea = ContentIdea(
        idea_id=idea_id,
        topic=topic,
        source_article_id=article.id,
        category=classification.category,
        source=f"{article.source}: {article.title}",
        why_it_matters=_why_it_matters(classification.category),
        target_audience=_target_audience(classification.category),
        suggested_angle=CATEGORY_ANGLES.get(
            classification.category,
            "Turn the source into a practical AI-native PM operating lesson.",
        ),
        hook_options=_hooks_for(classification.category),
        total_score=score.total_score,
        fluff_score=fluff.fluff_score,
        recommendation=score.recommendation,
    )
    preference_adjustment = calculate_preference_adjustment(base_idea)
    pillar = classify_pillar(article=article, idea=base_idea)
    positioning_score, positioning_warning, memory_recommendation = score_positioning(base_idea)
    article_quality = assess_title_quality(article)
    topic_quality = assess_topic_quality(base_idea)
    quality_warnings = list(dict.fromkeys(article_quality.warnings + topic_quality.warnings))
    quality_score = min(article_quality.quality_score, topic_quality.quality_score)
    quality_penalty = 0
    if "duplicate weak topic" in quality_warnings:
        quality_penalty -= 20
    final_score = max(0, score.total_score + preference_adjustment + pillar.score + quality_penalty)
    recommendation = _recommendation_for(final_score)
    if article_quality.reject_reason or topic_quality.reject_reason:
        recommendation = "reject"
    elif quality_warnings and recommendation == "post":
        recommendation = "park"
    return ContentIdea(
        idea_id=idea_id,
        topic=topic,
        source_article_id=article.id,
        category=classification.category,
        source=f"{article.source}: {article.title}",
        why_it_matters=_why_it_matters(classification.category),
        target_audience=_target_audience(classification.category),
        suggested_angle=CATEGORY_ANGLES.get(
            classification.category,
            "Turn the source into a practical AI-native PM operating lesson.",
        ),
        hook_options=_hooks_for(classification.category),
        total_score=score.total_score,
        fluff_score=fluff.fluff_score,
        recommendation=recommendation,
        preference_adjustment=preference_adjustment,
        final_score=final_score,
        primary_pillar=pillar.primary_pillar,
        secondary_pillar=pillar.secondary_pillar,
        pillar_confidence=pillar.confidence,
        pillar_score=pillar.score,
        positioning_fit_score=positioning_score,
        positioning_warning=positioning_warning,
        memory_recommendation=memory_recommendation,
        quality_score=quality_score,
        quality_warnings=quality_warnings,
        quality_reject_reason=article_quality.reject_reason or topic_quality.reject_reason,
    )


def recommend_articles(
    articles: list[Article],
    classifications: dict[str, ClassificationResult],
    scores: dict[str, ScoreResult],
) -> list[ContentIdea]:
    ideas = [
        build_content_idea(article, classifications[article.id], scores[article.id])
        for article in articles
    ]
    return sorted(ideas, key=lambda idea: idea.final_score or 0, reverse=True)


def _idea_id_for(category: str, topic: str) -> str:
    slug = "-".join(
        word.strip(".,:;!?").lower()
        for word in topic.split()
        if word.strip(".,:;!?")
    )
    return f"{category}::{slug}"


def _recommendation_for(final_score: int) -> str:
    if final_score >= 70:
        return "post"
    if final_score >= 50:
        return "park"
    return "reject"


def _topic_for(article: Article, category: str) -> str:
    if category == "ai_native_pm_mindset":
        return "AI-native PMs are not faster PRD writers"
    if category == "context_engineering":
        return "Context engineering is becoming a PM operating skill"
    if category == "ai_governance":
        return "AI governance is product work, not only policy work"
    if category == "enterprise_ai_operating_models":
        return "Enterprise AI needs workflow redesign before tool rollout"
    if category == "product_discovery_with_ai":
        return "AI can speed discovery only when PMs protect evidence quality"
    return article.title.rstrip(".")


def _why_it_matters(category: str) -> str:
    if category == "ai_native_pm_mindset":
        return (
            "Traditional PMs often use AI to speed up documentation. The bigger shift "
            "is using AI to improve discovery, validation, prioritization, and workflow orchestration."
        )
    if category == "context_engineering":
        return (
            "PMs who shape context, memory, and retrieval can improve the quality of AI-supported decisions."
        )
    if category == "ai_governance":
        return (
            "Enterprise PMs need to design controls, auditability, and escalation into AI-enabled workflows."
        )
    return (
        "The topic helps PMs move from generic AI usage toward practical AI-native operating habits."
    )


def _target_audience(category: str) -> str:
    if category in {"ai_governance", "enterprise_ai_operating_models"}:
        return "Enterprise PMs and product leaders adopting AI in regulated environments."
    return "Traditional PMs transitioning into AI PM roles."


def _hooks_for(category: str) -> list[str]:
    common = [
        "AI-native PM is not about writing PRDs faster.",
        "The next PM skill is not prompting. It is orchestration.",
        "Traditional PMs manage backlogs. AI-native PMs design decision loops.",
    ]
    if category == "context_engineering":
        return [
            "Context engineering may become the most underrated PM skill.",
            "Bad AI output is often a context design problem.",
            "PMs need to design what AI knows before asking what AI can do.",
        ]
    if category == "ai_governance":
        return [
            "AI governance becomes real when it changes product workflows.",
            "Controls are not bureaucracy when AI is making workflow decisions.",
            "The PM role in AI governance is designing the review loop.",
        ]
    return common
