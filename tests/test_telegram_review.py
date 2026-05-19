from pathlib import Path

from kaya_toast.models import ContentIdea
from kaya_toast.report import generate_report
from kaya_toast.telegram_review import handle_dry_run


def test_top_command_reads_latest_daily_report(tmp_path: Path, monkeypatch):
    import kaya_toast.telegram_review as telegram_review

    monkeypatch.setattr(telegram_review, "DAILY_REPORTS_DIR", tmp_path / "daily")
    _daily_report(tmp_path / "daily")

    result = handle_dry_run("/top")

    assert "Top ideas:" in result.response
    assert "Stakeholders and the Product Model" in result.response


def test_idea_command_maps_number_to_idea(tmp_path: Path, monkeypatch):
    import kaya_toast.telegram_review as telegram_review

    monkeypatch.setattr(telegram_review, "DAILY_REPORTS_DIR", tmp_path / "daily")
    _daily_report(tmp_path / "daily")

    result = handle_dry_run("/idea 1")

    assert "Idea ID: enterprise_ai_operating_models::stakeholders" in result.response


def test_feedback_dry_run_does_not_require_token(tmp_path: Path, monkeypatch):
    import kaya_toast.telegram_review as telegram_review

    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setattr(telegram_review, "DAILY_REPORTS_DIR", tmp_path / "daily")
    _daily_report(tmp_path / "daily")

    result = handle_dry_run("/like 1")

    assert "DRY RUN: would save like" in result.response


def test_help_mentions_no_linkedin_auto_posting():
    result = handle_dry_run("/help")

    assert "No LinkedIn auto-posting" in result.response


def _daily_report(output_dir: Path) -> Path:
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
    return generate_report([idea], output_dir)
