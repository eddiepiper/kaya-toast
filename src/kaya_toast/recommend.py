from __future__ import annotations

from kaya_toast.fluff import fluff_check
from kaya_toast.memory import score_positioning
from kaya_toast.models import Article, ClassificationResult, ContentIdea, ScoreResult
from kaya_toast.pillars import classify_pillar
from kaya_toast.preference import calculate_preference_adjustment
from kaya_toast.quality import assess_title_quality, assess_topic_quality, is_high_quality_title, source_quality_boost


FALLBACK_TOPICS = {
    "AI-native PMs are not faster PRD writers",
    "AI governance is product work, not only policy work",
    "Enterprise AI needs workflow redesign before tool rollout",
}

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
        source_url=article.url,
        source_summary=article.summary,
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
    boost = source_quality_boost(article)
    quality_penalty = 0
    if "duplicate weak topic" in quality_warnings:
        quality_penalty -= 20
    final_score = max(0, score.total_score + preference_adjustment + pillar.score + boost + quality_penalty)
    recommendation = _recommendation_for(final_score, high_quality=is_high_quality_title(article.title))
    if article_quality.reject_reason or topic_quality.reject_reason:
        recommendation = "reject"
    elif quality_warnings and recommendation == "post":
        recommendation = "park"
    recommendation = _apply_positioning_cap(
        recommendation,
        positioning_warning=positioning_warning,
        positioning_score=positioning_score,
        quality_score=quality_score,
    )
    return ContentIdea(
        idea_id=idea_id,
        topic=topic,
        source_article_id=article.id,
        category=classification.category,
        source=f"{article.source}: {article.title}",
        source_url=article.url,
        source_summary=article.summary,
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
        source_quality_boost=boost,
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
    return dedupe_content_ideas(sorted(ideas, key=lambda idea: idea.final_score or 0, reverse=True))


def dedupe_content_ideas(ideas: list[ContentIdea]) -> list[ContentIdea]:
    selected: dict[str, ContentIdea] = {}
    order: list[str] = []
    fallback_seen: set[str] = set()

    for idea in sorted(ideas, key=lambda item: item.final_score or 0, reverse=True):
        topic_key = _normalize_topic(idea.topic)
        if idea.topic in FALLBACK_TOPICS:
            if idea.topic in fallback_seen:
                continue
            fallback_seen.add(idea.topic)
        keys = [f"id:{idea.idea_id}", f"topic:{topic_key}"]
        existing_key = next((key for key in keys if key in selected), None)
        if existing_key is None:
            primary_key = keys[0]
            selected[primary_key] = idea
            selected[keys[1]] = idea
            order.append(primary_key)
            continue

        existing = selected[existing_key]
        if (idea.final_score or 0) > (existing.final_score or 0):
            primary_key = next(key for key in order if selected[key] == existing)
            selected[primary_key] = idea
            selected[keys[0]] = idea
            selected[keys[1]] = idea

    deduped: list[ContentIdea] = []
    seen_ids: set[str] = set()
    for key in order:
        idea = selected[key]
        if id(idea) in seen_ids:
            continue
        seen_ids.add(id(idea))
        deduped.append(idea)
    return deduped


def _idea_id_for(category: str, topic: str) -> str:
    slug = "-".join(
        word.strip(".,:;!?").lower()
        for word in topic.split()
        if word.strip(".,:;!?")
    )
    return f"{category}::{slug}"


def _recommendation_for(final_score: int, high_quality: bool = False) -> str:
    post_threshold = 65 if high_quality else 70
    if final_score >= post_threshold:
        return "post"
    if final_score >= 50:
        return "park"
    return "reject"


def _apply_positioning_cap(
    recommendation: str,
    positioning_warning: str | None,
    positioning_score: int,
    quality_score: int,
) -> str:
    capped_warnings = {"Sounds like prompt-bro content", "Too generic", "Weak positioning fit"}
    if (
        recommendation == "post"
        and positioning_warning in capped_warnings
        and not (positioning_score >= 40 and quality_score >= 80)
    ):
        return "park"
    return recommendation


def _topic_for(article: Article, category: str) -> str:
    if is_high_quality_title(article.title):
        return article.title.rstrip(".")
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
    hooks_by_category = {
        "ai_native_pm_mindset": [
            "AI-native PM is not about writing PRDs faster.",
            "The PM role is shifting from managing outputs to designing decision loops.",
        ],
        "agentic_workflows": [
            "Agentic workflows still need product judgment.",
            "The hard part of agentic workflows is not automation. It is control.",
        ],
        "ai_prototyping": [
            "AI prototyping is not just faster UI work.",
            "The real value of AI prototyping is faster product judgment.",
        ],
        "product_discovery_with_ai": [
            "AI can speed up discovery, but it cannot replace evidence quality.",
            "Discovery gets faster with AI only if PMs protect the signal.",
        ],
        "enterprise_ai_operating_models": [
            "Enterprise AI fails when tools arrive before workflows change.",
            "AI transformation is not a tooling rollout. It is an operating model redesign.",
        ],
        "ai_governance": [
            "AI governance is product work when decisions affect customers.",
            "Guardrails are not paperwork. They are part of the user journey.",
        ],
    }
    if category in hooks_by_category:
        return hooks_by_category[category]
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
    return [
        "The next PM skill is not prompting. It is orchestration.",
        "Traditional PMs manage backlogs. AI-native PMs design decision loops.",
    ]


def _normalize_topic(topic: str) -> str:
    return "".join(character for character in topic.lower() if character.isalnum())
