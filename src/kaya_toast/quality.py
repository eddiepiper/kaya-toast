from __future__ import annotations

import re

from kaya_toast.models import Article, ContentIdea, QualityResult


MEANINGFUL_KEYWORDS = [
    "pm",
    "product",
    "workflow",
    "ai",
    "enterprise",
    "governance",
    "strategy",
    "strategic",
    "agent",
    "context",
    "discovery",
    "decision",
    "operating",
    "risk",
    "compliance",
    "banking",
    "prototype",
    "customer",
]

HIGH_QUALITY_TITLE_KEYWORDS = [
    "pm",
    "product",
    "ai",
    "workflow",
    "enterprise",
    "governance",
    "strategy",
    "discovery",
    "customer",
]

PREFERRED_SOURCE_BOOSTS = {
    "Product Talk": 10,
    "SVPG Articles": 10,
    "Lenny's Newsletter": 8,
    "Google AI Blog": 8,
}

GENERIC_TITLES = {
    "fragments",
    "links",
    "notes",
    "updates",
    "weekly roundup",
    "roundup",
    "newsletter",
}


def assess_title_quality(article: Article) -> QualityResult:
    title = article.title.strip()
    lower_title = title.lower()
    warnings: list[str] = []
    quality_score = 100
    reject_reason = None

    if is_generic_fragment_title(title):
        warnings.append("generic fragment title")
        quality_score -= 75
        reject_reason = "generic fragment title"
    elif is_weak_title(title):
        warnings.append("weak source title")
        quality_score -= 40

    if lower_title in GENERIC_TITLES:
        warnings.append("too generic")
        quality_score -= 35
        reject_reason = reject_reason or "too generic"

    if not _has_meaningful_keyword(title):
        warnings.append("no clear PM content angle")
        quality_score -= 30

    return QualityResult(
        quality_score=max(0, quality_score),
        warnings=warnings,
        reject_reason=reject_reason,
    )


def assess_topic_quality(content_idea: ContentIdea) -> QualityResult:
    topic = content_idea.topic.strip()
    source_title = _source_title(content_idea.source)
    warnings: list[str] = []
    quality_score = 100
    reject_reason = None

    if is_generic_fragment_title(topic):
        warnings.append("generic fragment title")
        quality_score -= 75
        reject_reason = "generic fragment title"

    if is_weak_title(topic):
        warnings.append("weak generated topic")
        quality_score -= 40

    if _near_duplicate(topic, source_title) and (
        is_weak_title(source_title) or is_generic_fragment_title(source_title)
    ):
        warnings.append("duplicate weak topic")
        quality_score -= 20

    if not _has_meaningful_keyword(f"{topic} {content_idea.suggested_angle}"):
        warnings.append("no clear PM content angle")
        quality_score -= 30

    return QualityResult(
        quality_score=max(0, quality_score),
        warnings=warnings,
        reject_reason=reject_reason,
    )


def is_high_quality_title(title: str) -> bool:
    if is_generic_fragment_title(title) or is_weak_title(title):
        return False
    lowered = title.lower()
    return any(keyword in lowered for keyword in HIGH_QUALITY_TITLE_KEYWORDS)


def source_quality_boost(article: Article) -> int:
    if not is_high_quality_title(article.title):
        return 0
    return PREFERRED_SOURCE_BOOSTS.get(article.source, 0)


def is_weak_title(title: str) -> bool:
    stripped = title.strip()
    if len(stripped) < 12:
        return True
    if re.fullmatch(r"[A-Za-z]+\.?\s+\d{1,2}", stripped):
        return True
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stripped):
        return True
    if re.fullmatch(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}", stripped.lower()):
        return True
    return False


def is_generic_fragment_title(title: str) -> bool:
    return bool(re.match(r"^fragments:\s*[A-Za-z]+\s+\d{1,2}$", title.strip(), re.IGNORECASE))


def _has_meaningful_keyword(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in MEANINGFUL_KEYWORDS)


def _source_title(source: str) -> str:
    if ": " not in source:
        return source
    return source.split(": ", 1)[1]


def _near_duplicate(left: str, right: str) -> bool:
    return _normalize(left) == _normalize(right)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())
