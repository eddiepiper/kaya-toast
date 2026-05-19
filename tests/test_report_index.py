from pathlib import Path

from kaya_toast.report_index import generate_report_index, render_report_index


def test_render_report_index_contains_mobile_flow():
    text = render_report_index()

    assert "# kaya-toast Report Index" in text
    assert "## Latest Daily Brief" in text
    assert "## Latest Editorial Recommendation" in text
    assert "## Latest Drafts" in text
    assert "## Latest Voice Reviews" in text
    assert "## Latest Strategy Brief" in text
    assert "1. Read daily brief" in text
    assert "5. Give feedback later" in text


def test_generate_report_index_writes_file(tmp_path: Path):
    path = generate_report_index(tmp_path / "INDEX.md")

    assert path.exists()
    assert "Quick Mobile Review Flow" in path.read_text(encoding="utf-8")
