from pathlib import Path

from kaya_toast import cli
from kaya_toast.collect import CollectionResult, collect_from_rss_sources, normalize_rss_item
from kaya_toast.config import load_sources


def _sources_config():
    return {
        "sources": [
            {
                "name": "Good Source",
                "type": "rss",
                "url": "https://example.com/feed.xml",
                "max_items": 1,
                "tags": ["ai"],
            },
            {
                "name": "Bad Source",
                "type": "rss",
                "url": "https://example.com/bad.xml",
                "tags": ["ai"],
            },
        ]
    }


def test_sources_yaml_loads():
    sources = load_sources()

    assert "sources" in sources
    assert any(source["name"] == "OpenAI News" for source in sources["sources"])
    assert any(source["name"] == "Product Talk" for source in sources["sources"])


def test_rss_normalization_works():
    article = normalize_rss_item(
        {
            "title": "AI product workflow",
            "link": "https://example.com/workflow",
            "summary": "<p>PMs can design and review AI workflows.</p>",
            "published": "2026-05-18",
            "id": "workflow-1",
        },
        "Example RSS",
    )

    assert article.title == "AI product workflow"
    assert article.summary == "PMs can design and review AI workflows."
    assert article.source == "Example RSS"
    assert article.published_date == "2026-05-18"


def test_failed_rss_source_does_not_crash(monkeypatch):
    def fake_parse(url: str):
        if "bad" in url:
            raise ValueError("network failed")
        return [
            {
                "title": "Enterprise AI workflow",
                "link": "https://example.com/enterprise-ai",
                "summary": "Product managers design enterprise AI workflow review loops.",
            }
        ]

    monkeypatch.setattr("kaya_toast.collect._parse_rss", fake_parse)

    result = collect_from_rss_sources(_sources_config())

    assert len(result.articles) == 1
    assert result.counts_by_source["Good Source"] == 1
    assert result.counts_by_source["Bad Source"] == 0
    assert result.warnings == ["Bad Source: network failed"]


def test_collect_rss_command_works_with_mocked_data(tmp_path: Path, monkeypatch):
    def fake_collect(_sources):
        return CollectionResult(
            articles=[
                normalize_rss_item(
                    {
                        "title": "AI PM workflow",
                        "link": "https://example.com/ai-pm",
                        "summary": "Product managers design AI workflow review loops.",
                    },
                    "Mock Source",
                )
            ],
            counts_by_source={"Mock Source": 1},
            warnings=[],
        )

    monkeypatch.setattr(cli, "load_sources", lambda: {"sources": []})
    monkeypatch.setattr(cli, "collect_from_rss_sources", fake_collect)
    monkeypatch.setattr(cli, "save_articles_json", lambda articles: tmp_path / "latest.json")

    assert cli.main(["collect-rss"]) == 0


def test_run_rss_works_with_mocked_data(tmp_path: Path, monkeypatch):
    def fake_collect(_sources):
        return CollectionResult(
            articles=[
                normalize_rss_item(
                    {
                        "title": "Context engineering for PMs",
                        "link": "https://example.com/context",
                        "summary": "Product managers design context engineering memory and retrieval workflows.",
                    },
                    "Mock Source",
                )
            ],
            counts_by_source={"Mock Source": 1},
            warnings=[],
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_sources", lambda: {"sources": []})
    monkeypatch.setattr(cli, "collect_from_rss_sources", fake_collect)
    monkeypatch.setattr(cli, "save_articles_json", lambda articles: tmp_path / "latest.json")

    assert cli.main(["run", "--rss"]) == 0
    assert list((tmp_path / "reports").glob("*-kaya-toast.md"))
