import json
from pathlib import Path

import pytest

from kaya_toast.models import ContentIdea
from kaya_toast.preference import (
    add_feedback,
    calculate_preference_adjustment,
    load_feedback,
    save_feedback,
    summarize_feedback,
)


def _idea() -> ContentIdea:
    return ContentIdea(
        idea_id="context_engineering::context-engineering-is-becoming-a-pm-operating-skill",
        topic="Context engineering is becoming a PM operating skill",
        source_article_id="a3",
        category="context_engineering",
        source="AI Product Notes",
        why_it_matters="PMs can improve AI-supported decisions through better context.",
        target_audience="Traditional PMs transitioning into AI PM roles.",
        suggested_angle="Make context engineering concrete for PM decisions, memory, and retrieval.",
        hook_options=["Context engineering may become the most underrated PM skill."],
        total_score=65,
        fluff_score=0,
        recommendation="park",
    )


def test_feedback_file_created(tmp_path: Path):
    feedback_path = tmp_path / "data" / "feedback.json"

    records = load_feedback(feedback_path)

    assert records == []
    assert feedback_path.exists()
    assert json.loads(feedback_path.read_text(encoding="utf-8")) == []


def test_add_feedback(tmp_path: Path):
    feedback_path = tmp_path / "feedback.json"

    record = add_feedback("IDEA001", "like", "use this angle", feedback_path)

    assert record["idea_id"] == "IDEA001"
    assert record["rating"] == "like"
    assert load_feedback(feedback_path)[0]["notes"] == "use this angle"


def test_invalid_rating_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        add_feedback("IDEA001", "amazing", path=tmp_path / "feedback.json")


def test_preference_adjustment_affects_future_idea_scores(tmp_path: Path):
    feedback_path = tmp_path / "feedback.json"
    add_feedback(
        "context_engineering::context-engineering-is-becoming-a-pm-operating-skill",
        "like",
        path=feedback_path,
    )

    adjustment = calculate_preference_adjustment(_idea(), feedback_path)

    assert adjustment == 10
    assert _idea().total_score + adjustment == 75


def test_summarize_feedback_counts_liked_and_rejected_categories(tmp_path: Path):
    feedback_path = tmp_path / "feedback.json"
    save_feedback(
        [
            {
                "idea_id": "context_engineering::context-engineering-is-becoming-a-pm-operating-skill",
                "rating": "like",
                "timestamp": "2026-05-18T00:00:00+00:00",
                "notes": "",
            },
            {
                "idea_id": "ai_native_pm_mindset::ai-native-pms-are-not-faster-prd-writers",
                "rating": "too_generic",
                "timestamp": "2026-05-18T00:00:00+00:00",
                "notes": "",
            },
        ],
        feedback_path,
    )

    summary = summarize_feedback(feedback_path)

    assert summary["total_records"] == 2
    assert summary["most_liked_categories"] == ["context_engineering"]
    assert summary["most_rejected_categories"] == ["ai_native_pm_mindset"]
