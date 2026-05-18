from pathlib import Path

import pytest

from kaya_toast.cli import main, run_pipeline
from kaya_toast.report import generate_report, render_report
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
    assert "## Parked But Promising" in path.read_text(encoding="utf-8")
    assert "## Preference Memory" in path.read_text(encoding="utf-8")
    assert "## Source Summary" in path.read_text(encoding="utf-8")
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


def _idea(index: int, section: str) -> ContentIdea:
    return ContentIdea(
        idea_id=f"{section}-{index}",
        topic=f"{section} topic {index}",
        source_article_id=f"a{index}",
        category="ai_native_pm_mindset",
        source=f"Source: {section} topic {index}",
        why_it_matters="It matters.",
        target_audience="Traditional PMs",
        suggested_angle="Make it practical.",
        hook_options=["AI-native PM is not about writing PRDs faster."],
        total_score=10,
        fluff_score=50 if section == "fluff" else 0,
        recommendation="reject",
        quality_warnings=["no clear PM content angle"] if section == "quality" else [],
    )


def test_rejected_fluff_and_quality_sections_are_capped():
    rejected = [_idea(index, "rejected") for index in range(7)]
    fluff = [_idea(index, "fluff") for index in range(12)]
    quality = [_idea(index, "quality") for index in range(12)]

    report = render_report(rejected + fluff + quality)

    rejected_section = report.split("## Rejected Ideas", 1)[1].split("## Fluff Warnings", 1)[0]
    fluff_section = report.split("## Fluff Warnings", 1)[1].split("## Quality Warnings", 1)[0]
    quality_section = report.split("## Quality Warnings", 1)[1]
    assert rejected_section.count("### ") == 5
    assert fluff_section.count("- ") == 10
    assert quality_section.count("- ") == 10


def test_parked_idea_is_rendered_once_as_promising():
    idea = ContentIdea(
        idea_id="parked",
        topic="Specific parked topic",
        source_article_id="a1",
        category="ai_native_pm_mindset",
        source="Source: Specific parked topic",
        why_it_matters="It matters.",
        target_audience="Traditional PMs",
        suggested_angle="Make it practical.",
        hook_options=["AI-native PM is not about writing PRDs faster."],
        total_score=50,
        fluff_score=0,
        recommendation="park",
        final_score=55,
    )

    report = render_report([idea])

    assert "## Parked Ideas" not in report
    assert report.count("### Specific parked topic") == 1
