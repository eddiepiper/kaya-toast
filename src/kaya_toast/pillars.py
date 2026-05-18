from __future__ import annotations

from dataclasses import dataclass

from kaya_toast.models import Article, ContentIdea


PILLAR_BOOSTS = {
    "ai_native_pm": 15,
    "ai_native_banking": 8,
    "founder_systems": 6,
    "healthcare_caregiver_ai": 6,
}

PILLAR_KEYWORDS = {
    "ai_native_pm": [
        "product manager",
        "product management",
        "ai-native",
        "ai pm",
        "workflow",
        "discovery",
        "roadmap",
        "prioritize",
    ],
    "ai_native_banking": [
        "bank",
        "banking",
        "fintech",
        "risk",
        "compliance",
        "audit",
        "controls",
        "regulated",
    ],
    "founder_systems": [
        "founder",
        "startup",
        "solo",
        "small team",
        "leverage",
        "operator",
        "building",
    ],
    "healthcare_caregiver_ai": [
        "healthcare",
        "health",
        "caregiver",
        "elderly",
        "patient",
        "clinical",
        "care",
    ],
}


@dataclass(frozen=True)
class PillarResult:
    primary_pillar: str
    secondary_pillar: str | None
    confidence: float
    score: int


def classify_pillar(article: Article | None = None, idea: ContentIdea | None = None) -> PillarResult:
    text = ""
    if article is not None:
        text += f" {article.title} {article.summary} {article.source}"
    if idea is not None:
        text += f" {idea.topic} {idea.suggested_angle} {idea.why_it_matters} {idea.source}"
    text = text.lower()

    counts = {
        pillar: sum(1 for keyword in keywords if keyword in text)
        for pillar, keywords in PILLAR_KEYWORDS.items()
    }
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    primary, primary_count = ranked[0]
    if primary_count == 0:
        primary = "ai_native_pm"
        primary_count = 1

    secondary = None
    if len(ranked) > 1 and ranked[1][1] > 0:
        secondary = ranked[1][0]

    confidence = min(1.0, primary_count / 4)
    return PillarResult(
        primary_pillar=primary,
        secondary_pillar=secondary,
        confidence=round(confidence, 2),
        score=PILLAR_BOOSTS[primary],
    )


def filter_by_pillar(ideas: list[ContentIdea], pillar: str) -> list[ContentIdea]:
    if pillar == "all":
        return ideas
    return [
        idea
        for idea in ideas
        if idea.primary_pillar == pillar or idea.secondary_pillar == pillar
    ]
