from pathlib import Path

from kaya_toast.v2_flow import V2FlowResult, render_v2_flow_result, run_v2_flow


def test_render_v2_flow_result_lists_paths(tmp_path: Path):
    result = V2FlowResult(
        daily_report=tmp_path / "daily.md",
        editorial_report=tmp_path / "editorial.md",
        source_review_reports=[tmp_path / "source.md"],
        draft_files=[tmp_path / "draft.md"],
        voice_review_reports=[tmp_path / "voice.md"],
        index_path=tmp_path / "INDEX.md",
    )

    text = render_v2_flow_result(result)

    assert "Daily report:" in text
    assert "Editorial report:" in text
    assert "Source review reports:" in text
    assert "Draft files:" in text
    assert "Voice review reports:" in text
    assert "Report index:" in text


def test_run_v2_flow_orchestrates_steps(tmp_path: Path, monkeypatch):
    import kaya_toast.v2_flow as v2_flow

    monkeypatch.setattr(v2_flow, "run_daily", lambda: tmp_path / "daily.md")
    monkeypatch.setattr(v2_flow, "generate_editorial_report", lambda _daily: tmp_path / "editorial.md")
    monkeypatch.setattr(v2_flow, "generate_source_reviews", lambda _daily, top: [tmp_path / f"source-{top}.md"])
    monkeypatch.setattr(v2_flow, "draft_from_report", lambda _daily, top, use_source_review: [tmp_path / f"draft-{top}.md"])
    monkeypatch.setattr(v2_flow, "generate_all_latest_voice_reviews", lambda: [tmp_path / "voice.md"])
    monkeypatch.setattr(v2_flow, "generate_report_index", lambda: tmp_path / "INDEX.md")

    result = run_v2_flow(top=2)

    assert result.daily_report == tmp_path / "daily.md"
    assert result.source_review_reports == [tmp_path / "source-2.md"]
    assert result.draft_files == [tmp_path / "draft-2.md"]
