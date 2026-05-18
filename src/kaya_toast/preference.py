from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaya_toast.models import ContentIdea


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEEDBACK_PATH = PROJECT_ROOT / "data" / "feedback.json"

SUPPORTED_RATINGS = {
    "like",
    "dislike",
    "use_later",
    "too_fluffy",
    "too_generic",
    "too_technical",
    "strong_angle",
    "weak_angle",
}

RATING_WEIGHTS = {
    "like": 10,
    "strong_angle": 8,
    "use_later": 4,
    "dislike": -10,
    "too_fluffy": -15,
    "too_generic": -12,
    "too_technical": -8,
    "weak_angle": -8,
}


def load_feedback(path: str | Path = FEEDBACK_PATH) -> list[dict[str, Any]]:
    feedback_path = Path(path)
    if not feedback_path.exists():
        save_feedback([], feedback_path)

    with feedback_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"Feedback file must contain a list: {feedback_path}")
    return data


def save_feedback(
    records: list[dict[str, Any]],
    path: str | Path = FEEDBACK_PATH,
) -> None:
    feedback_path = Path(path)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(
        json.dumps(records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def add_feedback(
    idea_id: str,
    rating: str,
    notes: str = "",
    path: str | Path = FEEDBACK_PATH,
) -> dict[str, Any]:
    if rating not in SUPPORTED_RATINGS:
        allowed = ", ".join(sorted(SUPPORTED_RATINGS))
        raise ValueError(f"Unsupported rating '{rating}'. Supported ratings: {allowed}")

    records = load_feedback(path)
    record = {
        "idea_id": idea_id,
        "rating": rating,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }
    records.append(record)
    save_feedback(records, path)
    return record


def summarize_feedback(
    path: str | Path = FEEDBACK_PATH,
) -> dict[str, Any]:
    records = load_feedback(path)
    rating_counts = Counter(record["rating"] for record in records)
    category_scores: dict[str, int] = {}

    for record in records:
        category = _category_from_idea_id(str(record.get("idea_id", "")))
        if not category:
            continue
        category_scores[category] = category_scores.get(category, 0) + RATING_WEIGHTS.get(
            str(record.get("rating", "")),
            0,
        )

    liked = [
        category
        for category, _score in sorted(
            ((category, score) for category, score in category_scores.items() if score > 0),
            key=lambda item: item[1],
            reverse=True,
        )
    ]
    rejected = [
        category
        for category, _score in sorted(
            ((category, score) for category, score in category_scores.items() if score < 0),
            key=lambda item: item[1],
        )
    ]

    return {
        "total_records": len(records),
        "rating_counts": dict(rating_counts),
        "most_liked_categories": liked,
        "most_rejected_categories": rejected,
        "category_scores": category_scores,
    }


def calculate_preference_adjustment(
    content_idea: ContentIdea,
    path: str | Path = FEEDBACK_PATH,
) -> int:
    records = load_feedback(path)
    adjustment = 0
    for record in records:
        weight = RATING_WEIGHTS.get(str(record.get("rating", "")), 0)
        if weight == 0:
            continue

        idea_id = str(record.get("idea_id", ""))
        if idea_id == content_idea.idea_id:
            adjustment += weight
            continue

        category = _category_from_idea_id(idea_id)
        topic_keywords = _keywords_from_idea_id(idea_id)
        if category and category == content_idea.category:
            adjustment += weight
            continue
        if topic_keywords and _matches_keywords(content_idea, topic_keywords):
            adjustment += weight

    return adjustment


def _category_from_idea_id(idea_id: str) -> str:
    if "::" not in idea_id:
        return ""
    return idea_id.split("::", 1)[0]


def _keywords_from_idea_id(idea_id: str) -> list[str]:
    if "::" not in idea_id:
        return []
    raw_keywords = idea_id.split("::", 1)[1].replace("-", " ").split()
    return [keyword for keyword in raw_keywords if len(keyword) >= 4]


def _matches_keywords(content_idea: ContentIdea, keywords: list[str]) -> bool:
    text = f"{content_idea.topic} {content_idea.suggested_angle}".lower()
    return any(keyword.lower() in text for keyword in keywords)
