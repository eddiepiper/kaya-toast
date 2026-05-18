import json
from pathlib import Path

from kaya_toast.config import load_positioning
from kaya_toast.memory import load_memory, score_positioning, update_memory_from_feedback
from kaya_toast.models import ContentIdea
from kaya_toast.report import render_report


def _idea(topic: str = "AI-native PMs design workflow loops") -> ContentIdea:
    return ContentIdea(
        idea_id="ai_native_pm::workflow-loops",
        topic=topic,
        source_article_id="a1",
        category="ai_native_pm_mindset",
        source="Mock",
        why_it_matters="Traditional PMs need practical workflow redesign.",
        target_audience="Traditional PMs",
        suggested_angle="Show practical enterprise workflow design.",
        hook_options=["AI-native PM is about decision loops."],
        total_score=80,
        fluff_score=0,
        recommendation="post",
        primary_pillar="ai_native_pm",
    )


def test_memory_file_is_created(tmp_path: Path):
    memory_path = tmp_path / "thinking_memory.json"

    memory = load_memory(memory_path)

    assert memory_path.exists()
    assert memory["recurring_liked_themes"] == []


def test_memory_updates_from_feedback(tmp_path: Path):
    memory_path = tmp_path / "thinking_memory.json"
    feedback_path = tmp_path / "feedback.json"
    feedback_path.write_text(
        json.dumps(
            [
                {
                    "idea_id": "ai_native_pm::workflow-loops",
                    "rating": "like",
                    "timestamp": "2026-05-18T00:00:00+00:00",
                    "notes": "",
                },
                {
                    "idea_id": "ai_native_pm::top-10-prompts",
                    "rating": "too_generic",
                    "timestamp": "2026-05-18T00:00:00+00:00",
                    "notes": "",
                },
            ]
        ),
        encoding="utf-8",
    )

    memory = update_memory_from_feedback(memory_path, feedback_path)

    assert "workflow" in memory["recurring_liked_themes"]
    assert "generic" in memory["disliked_styles"]


def test_positioning_config_loads():
    config = load_positioning()

    assert "AI-native PM practitioner" in config["desired_positioning"]
    assert "prompt bro" in config["avoid_positioning"]


def test_positioning_score_is_applied():
    score, warning, recommendation = score_positioning(_idea())

    assert score > 0
    assert warning in {"Good AI-native PM transition angle", "Strong enterprise operator fit"}
    assert recommendation == "Memory-aligned"


def test_bad_positioning_triggers_warning():
    score, warning, recommendation = score_positioning(
        _idea("Top 10 prompts to replace PMs and become an AI guru")
    )

    assert score < 30
    assert warning in {"Sounds like prompt-bro content", "Conflicts with desired positioning"}
    assert recommendation == "Review positioning before using"


def test_reports_include_positioning_fit():
    idea = _idea()
    idea = ContentIdea(
        **{
            **idea.__dict__,
            "positioning_fit_score": 45,
            "positioning_warning": "Good AI-native PM transition angle",
            "memory_recommendation": "Memory-aligned",
        }
    )

    report = render_report([idea])

    assert "Positioning fit: 45" in report
    assert "Memory-informed recommendation: Memory-aligned" in report
