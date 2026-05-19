from pathlib import Path

from kaya_toast.cli import main
from kaya_toast.editorial import EditorialContext, generate_editorial_report, render_editorial_report
from kaya_toast.models import ContentIdea
from kaya_toast.report import generate_report


def test_render_editorial_report_recommends_draft_for_strong_post(tmp_path: Path):
    daily_report = tmp_path / "2026-05-19-kaya-toast.md"
    strategy_report = tmp_path / "2026-05-19-kaya-toast-strategy.md"
    strategy_report.write_text("## Recommended Content Bets\n\n- Strong PM topic\n", encoding="utf-8")
    context = EditorialContext(
        daily_report_path=daily_report,
        strategy_report_path=strategy_report,
        preferences={"dislikes": {"angles": ["generic_productivity_hacks"]}},
        positioning={
            "desired_positioning": ["AI-native PM practitioner", "enterprise AI operator"],
            "avoid_positioning": ["AI guru", "prompt bro"],
        },
        feedback_summary={
            "most_liked_categories": ["enterprise_ai_operating_models"],
            "most_rejected_categories": [],
        },
    )
    ideas = [
        {
            "topic": "Strong PM topic",
            "idea_id": "enterprise_ai_operating_models::strong-pm-topic",
            "category": "enterprise_ai_operating_models",
            "recommendation": "post",
            "final_score": "85",
            "fluff_risk": "0",
            "positioning_fit": "45",
            "target_audience": "Enterprise PMs",
            "suggested_angle": "Connect enterprise AI strategy to PM workflow and decision design.",
            "memory-informed_recommendation": "Memory-aligned",
        },
        {
            "topic": "Parked topic",
            "idea_id": "ai_pm_skills::parked-topic",
            "recommendation": "park",
            "final_score": "77",
            "fluff_risk": "0",
        },
    ]

    report = render_editorial_report(ideas, context)

    assert "## Today's Recommended Idea" in report
    assert "- Topic: Strong PM topic" in report
    assert "## Why Not The Other Top Ideas" in report
    assert "## Stronger Operator Framing" in report
    assert "draft" in report.split("## Recommended Next Action", 1)[1]


def test_generate_editorial_report_writes_expected_path(tmp_path: Path):
    idea = ContentIdea(
        idea_id="enterprise_ai_operating_models::stakeholders",
        topic="Stakeholders and the Product Model",
        source_article_id="a1",
        category="enterprise_ai_operating_models",
        source="SVPG",
        why_it_matters="It shifts PMs from documentation speed to decision quality.",
        target_audience="Enterprise PMs and product leaders adopting AI.",
        suggested_angle="Connect enterprise AI strategy to PM workflow and decision design.",
        hook_options=["Enterprise AI fails when tools arrive before workflows change."],
        total_score=50,
        fluff_score=0,
        recommendation="post",
        final_score=85,
        positioning_fit_score=45,
        memory_recommendation="Memory-aligned",
    )
    daily_path = generate_report([idea], tmp_path / "daily")

    editorial_path = generate_editorial_report(daily_path, output_dir=tmp_path / "editorial")

    assert editorial_path == tmp_path / "editorial" / "2026-05-19-kaya-toast-editorial.md"
    assert editorial_path.exists()
    text = editorial_path.read_text(encoding="utf-8")
    assert "Stakeholders and the Product Model" in text
    assert "deterministic editorial fallback used" in text


def test_cli_editorial_command(tmp_path: Path, monkeypatch):
    import kaya_toast.editorial as editorial

    monkeypatch.setattr(editorial, "EDITORIAL_REPORTS_DIR", tmp_path / "editorial")
    idea = ContentIdea(
        idea_id="enterprise_ai_operating_models::stakeholders",
        topic="Stakeholders and the Product Model",
        source_article_id="a1",
        category="enterprise_ai_operating_models",
        source="SVPG",
        why_it_matters="It shifts PMs from documentation speed to decision quality.",
        target_audience="Enterprise PMs and product leaders adopting AI.",
        suggested_angle="Connect enterprise AI strategy to PM workflow and decision design.",
        hook_options=["Enterprise AI fails when tools arrive before workflows change."],
        total_score=50,
        fluff_score=0,
        recommendation="post",
        final_score=85,
    )
    daily_path = generate_report([idea], tmp_path)

    result = main(["editorial", "--report", str(daily_path)])

    assert result == 0
    assert (tmp_path / "editorial" / "2026-05-19-kaya-toast-editorial.md").exists()
