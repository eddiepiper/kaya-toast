from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kaya_toast.locking import atomic_json_write, file_lock, load_json_with_backup
from kaya_toast.models import ContentIdea


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEEDBACK_PATH = PROJECT_ROOT / "data" / "feedback.json"
FEEDBACK_BACKUP_PATH = PROJECT_ROOT / "data" / "feedback.backup.json"

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
    data = load_json_with_backup(feedback_path, [], _backup_path(feedback_path))

    if not isinstance(data, list):
        raise ValueError(f"Feedback file must contain a list: {feedback_path}")
    return data


def save_feedback(
    records: list[dict[str, Any]],
    path: str | Path = FEEDBACK_PATH,
) -> None:
    feedback_path = Path(path)
    with file_lock(_lock_path(feedback_path)):
        atomic_json_write(records, feedback_path, _backup_path(feedback_path))


def add_feedback(
    idea_id: str,
    rating: str,
    notes: str = "",
    path: str | Path = FEEDBACK_PATH,
) -> dict[str, Any]:
    if rating not in SUPPORTED_RATINGS:
        allowed = ", ".join(sorted(SUPPORTED_RATINGS))
        raise ValueError(f"Unsupported rating '{rating}'. Supported ratings: {allowed}")

    feedback_path = Path(path)
    with file_lock(_lock_path(feedback_path)):
        records = load_feedback(feedback_path)
        record = {
            "idea_id": idea_id,
            "rating": rating,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }
        records.append(record)
        atomic_json_write(records, feedback_path, _backup_path(feedback_path))
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


def _backup_path(feedback_path: Path) -> Path:
    if feedback_path == FEEDBACK_PATH:
        return FEEDBACK_BACKUP_PATH
    return feedback_path.with_name(f"{feedback_path.stem}.backup{feedback_path.suffix}")


def _lock_path(feedback_path: Path) -> Path:
    return feedback_path.with_suffix(f"{feedback_path.suffix}.lock")
