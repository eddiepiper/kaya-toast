from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from kaya_toast.config import load_positioning
from kaya_toast.locking import atomic_json_write, load_json_with_backup
from kaya_toast.models import ContentIdea
from kaya_toast.preference import load_feedback


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEMORY_PATH = PROJECT_ROOT / "data" / "thinking_memory.json"

DEFAULT_MEMORY = {
    "recurring_liked_themes": [],
    "recurring_rejected_themes": [],
    "preferred_angles": [],
    "disliked_styles": [],
    "strongest_positioning_phrases": [],
    "repeated_audience_focus": [],
    "content_ideas_used": [],
    "content_ideas_parked": [],
}

POSITIVE_RATINGS = {"like", "strong_angle", "use_later"}
NEGATIVE_RATINGS = {"dislike", "too_fluffy", "too_generic", "too_technical", "weak_angle"}


def load_memory(path: str | Path = MEMORY_PATH) -> dict[str, Any]:
    memory_path = Path(path)
    data = load_json_with_backup(memory_path, DEFAULT_MEMORY.copy())
    merged = DEFAULT_MEMORY.copy()
    merged.update(data)
    return merged


def save_memory(memory: dict[str, Any], path: str | Path = MEMORY_PATH) -> None:
    memory_path = Path(path)
    atomic_json_write(memory, memory_path)


def update_memory_from_feedback(
    memory_path: str | Path = MEMORY_PATH,
    feedback_path: str | Path | None = None,
) -> dict[str, Any]:
    memory = load_memory(memory_path)
    feedback = load_feedback(feedback_path) if feedback_path is not None else load_feedback()
    liked = [record["idea_id"] for record in feedback if record.get("rating") in POSITIVE_RATINGS]
    rejected = [record["idea_id"] for record in feedback if record.get("rating") in NEGATIVE_RATINGS]

    memory["content_ideas_used"] = sorted(set(memory["content_ideas_used"]) | set(liked))
    memory["content_ideas_parked"] = sorted(set(memory["content_ideas_parked"]) | set(rejected))
    memory["recurring_liked_themes"] = _top_tokens(liked)
    memory["recurring_rejected_themes"] = _top_tokens(rejected)
    memory["preferred_angles"] = _top_tokens(liked, min_length=5)
    memory["disliked_styles"] = _styles_from_negative_feedback(feedback)
    memory["strongest_positioning_phrases"] = [
        "AI-native PM practitioner",
        "enterprise AI operator",
        "practical AI workflow builder",
    ]
    memory["repeated_audience_focus"] = [
        "traditional PMs",
        "enterprise PMs",
        "AI-native PM transition",
    ]
    save_memory(memory, memory_path)
    return memory


def score_positioning(idea: ContentIdea, positioning_config: dict[str, Any] | None = None) -> tuple[int, str | None, str]:
    config = positioning_config or load_positioning()
    text = f"{idea.topic} {idea.suggested_angle} {idea.why_it_matters} {idea.category}".lower()
    desired = [phrase.lower() for phrase in config.get("desired_positioning", [])]
    avoided = [phrase.lower() for phrase in config.get("avoid_positioning", [])]

    score = 0
    warning = None
    if idea.primary_pillar == "ai_native_pm":
        score += 25
    if any(term in text for term in ["enterprise", "governance", "workflow", "operator", "banking"]):
        score += 20
    if any(term in text for term in ["prompt", "top 10", "productivity hack", "guru", "replace"]):
        score -= 25
        warning = "Sounds like prompt-bro content" if "prompt" in text else "Too generic"
    if any(_phrase_matches(text, phrase) for phrase in desired):
        score += 10
    if any(_phrase_matches(text, phrase) for phrase in avoided):
        score -= 20
        warning = warning or "Conflicts with desired positioning"

    if warning is None and score >= 35:
        warning = "Good AI-native PM transition angle"
    elif warning is None and score >= 20:
        warning = "Strong enterprise operator fit"
    elif warning is None:
        warning = "Too generic"

    recommendation = "Memory-aligned" if score >= 30 else "Review positioning before using"
    return max(0, min(100, score)), warning, recommendation


def summarize_memory(memory: dict[str, Any] | None = None) -> str:
    data = memory or load_memory()
    return "\n".join(
        [
            "kaya-toast Thinking Memory",
            f"- Recurring liked themes: {', '.join(data['recurring_liked_themes']) or 'None'}",
            f"- Recurring rejected themes: {', '.join(data['recurring_rejected_themes']) or 'None'}",
            f"- Preferred angles: {', '.join(data['preferred_angles']) or 'None'}",
            f"- Disliked styles: {', '.join(data['disliked_styles']) or 'None'}",
            f"- Strongest positioning phrases: {', '.join(data['strongest_positioning_phrases']) or 'None'}",
            f"- Repeated audience focus: {', '.join(data['repeated_audience_focus']) or 'None'}",
            f"- Content ideas used: {len(data['content_ideas_used'])}",
            f"- Content ideas parked: {len(data['content_ideas_parked'])}",
        ]
    )


def _top_tokens(values: list[str], min_length: int = 4) -> list[str]:
    tokens: list[str] = []
    for value in values:
        tokens.extend(
            token
            for token in value.replace("::", "-").replace("_", "-").split("-")
            if len(token) >= min_length
        )
    return [token for token, _count in Counter(tokens).most_common(8)]


def _styles_from_negative_feedback(feedback: list[dict[str, Any]]) -> list[str]:
    styles = []
    for record in feedback:
        rating = record.get("rating")
        if rating == "too_fluffy":
            styles.append("fluffy")
        elif rating == "too_generic":
            styles.append("generic")
        elif rating == "too_technical":
            styles.append("too technical without PM link")
        elif rating == "weak_angle":
            styles.append("weak angle")
    return sorted(set(styles))


def _phrase_matches(text: str, phrase: str) -> bool:
    words = [word for word in phrase.lower().replace("-", " ").split() if len(word) > 2]
    if not words:
        return False
    return all(word in text for word in words)
