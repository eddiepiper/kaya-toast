from pathlib import Path

from kaya_toast.cli import main
from kaya_toast.models import ContentIdea
from kaya_toast.report import generate_report
from kaya_toast.source_review import (
    generate_source_reviews,
    render_source_review,
    source_quality_score,
)


def test_source_review_command_creates_report(tmp_path: Path, monkeypatch):
    import kaya_toast.source_review as source_review

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(source_review, "SOURCE_REVIEW_DIR", tmp_path / "source_review")
    daily_path = _daily_report(tmp_path)

    result = main(
        [
            "source-review",
            "--idea-id",
            "enterprise_ai_operating_models::stakeholders",
            "--report",
            str(daily_path),
        ]
    )

    assert result == 0
    paths = list((tmp_path / "source_review").glob("*-source-review.md"))
    assert len(paths) == 1
    text = paths[0].read_text(encoding="utf-8")
    assert "## Unsupported Claims to Avoid" in text
    assert "## Source Quality Score" in text


def test_top_three_creates_up_to_three_reports(tmp_path: Path):
    daily_path = _daily_report(tmp_path, count=4)

    paths = generate_source_reviews(daily_path, top=3, output_dir=tmp_path / "reviews")

    assert len(paths) == 3
    assert all(path.exists() for path in paths)


def test_missing_api_key_does_not_fail(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    daily_path = _daily_report(tmp_path)

    paths = generate_source_reviews(daily_path, top=1, output_dir=tmp_path / "reviews")

    assert len(paths) == 1
    assert "deterministic" not in paths[0].read_text(encoding="utf-8").lower()


def test_deterministic_fallback_works():
    text = render_source_review(_strong_idea())

    assert "traditional PMs transitioning into AI-native PM roles" in text
    assert "Missing source summary in daily report" in text
    assert "Recommended action: draft" in text


def test_weak_source_gets_lower_quality_score():
    strong = source_quality_score(_strong_idea())
    weak = source_quality_score(
        {
            "topic": "AI news",
            "idea_id": "generic::ai-news",
            "category": "generic_ai_tools",
            "source": "Unknown",
            "suggested_angle": "Summarize AI news.",
            "recommendation": "reject",
            "fluff_risk": "50",
            "quality_warnings": "no clear PM content angle",
        }
    )

    assert weak < strong
    assert weak < 50


def test_source_review_does_not_alter_daily_report(tmp_path: Path):
    daily_path = _daily_report(tmp_path)
    before = daily_path.read_text(encoding="utf-8")

    generate_source_reviews(daily_path, top=1, output_dir=tmp_path / "reviews")

    assert daily_path.read_text(encoding="utf-8") == before


def _daily_report(tmp_path: Path, count: int = 1) -> Path:
    ideas = []
    for index in range(count):
        ideas.append(
            ContentIdea(
                idea_id=(
                    "enterprise_ai_operating_models::stakeholders"
                    if index == 0
                    else f"agentic_workflows::review-loop-{index}"
                ),
                topic=(
                    "Stakeholders and the Product Model"
                    if index == 0
                    else f"Agentic review loop {index}"
                ),
                source_article_id=f"a{index}",
                category="enterprise_ai_operating_models" if index == 0 else "agentic_workflows",
                source=(
                    "SVPG Articles: Stakeholders and the Product Model"
                    if index == 0
                    else f"Example Source: Agentic review loop {index}"
                ),
                why_it_matters="It shifts PMs from documentation speed to decision quality.",
                target_audience="Enterprise PMs and product leaders adopting AI.",
                suggested_angle="Connect enterprise AI strategy to PM workflow and decision design.",
                hook_options=["Enterprise AI fails when tools arrive before workflows change."],
                total_score=50,
                fluff_score=0,
                recommendation="post",
                final_score=85 - index,
                positioning_fit_score=45,
            )
        )
    return generate_report(ideas, tmp_path / "daily")


def _strong_idea() -> dict[str, str]:
    return {
        "topic": "Stakeholders and the Product Model",
        "idea_id": "enterprise_ai_operating_models::stakeholders",
        "category": "enterprise_ai_operating_models",
        "source": "SVPG Articles: Stakeholders and the Product Model",
        "why_it_matters": "It shifts PMs from documentation speed to decision quality.",
        "target_audience": "Enterprise PMs and product leaders adopting AI.",
        "suggested_angle": "Connect enterprise AI strategy to PM workflow and decision design.",
        "positioning_warning": "Strong enterprise operator fit",
        "quality_warnings": "None",
        "recommendation": "post",
        "fluff_risk": "0",
    }
