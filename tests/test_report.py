from pathlib import Path

import pytest

from kaya_toast.cli import main, run_pipeline
from kaya_toast.report import generate_report
from kaya_toast.models import ContentIdea


def test_report_file_is_created(tmp_path: Path):
    idea = ContentIdea(
        idea_id="idea-test",
        topic="AI-native PMs are not faster PRD writers",
        source_article_id="a1",
        category="ai_native_pm_mindset",
        source="Example Source",
        why_it_matters="It shifts PMs from documentation speed to decision quality.",
        target_audience="Traditional PMs transitioning into AI PM roles.",
        suggested_angle="Challenge the productivity-only misconception.",
        hook_options=["AI-native PM is not about writing PRDs faster."],
        total_score=80,
        fluff_score=0,
        recommendation="post",
    )

    path = generate_report([idea], tmp_path)

    assert path.exists()
    assert "## Top LinkedIn Content Ideas" in path.read_text(encoding="utf-8")
    assert "## Preference Memory" in path.read_text(encoding="utf-8")
    assert "Preference Adjustment:" in path.read_text(encoding="utf-8")
    assert "Final Score:" in path.read_text(encoding="utf-8")


def test_cli_run_works(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_sample = Path(__file__).resolve().parents[1] / "examples" / "sample_articles.json"

    result = main(["run", "--input", str(project_sample)])

    assert result == 0
    assert list((tmp_path / "reports").glob("*-kaya-toast.md"))


def test_cli_invalid_feedback_rating_rejected():
    with pytest.raises(SystemExit):
        main(["feedback", "--idea-id", "IDEA001", "--rating", "amazing"])


def test_run_pipeline_returns_report_path(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    project_sample = Path(__file__).resolve().parents[1] / "examples" / "sample_articles.json"

    path = run_pipeline(project_sample)

    assert path.exists()
    assert path.name.endswith("-kaya-toast.md")
