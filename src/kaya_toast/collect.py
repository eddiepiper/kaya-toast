from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kaya_toast.models import Article


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LATEST_RSS_PATH = PROJECT_ROOT / "data" / "latest_rss_articles.json"


@dataclass(frozen=True)
class CollectionResult:
    articles: list[Article]
    counts_by_source: dict[str, int]
    warnings: list[str] = field(default_factory=list)


def collect_from_json(input_path: str | Path) -> list[Article]:
    path = _resolve_input_path(input_path)
    with path.open("r", encoding="utf-8") as file:
        raw_articles = json.load(file)

    if not isinstance(raw_articles, list):
        raise ValueError("Input JSON must be a list of article objects")

    articles: list[Article] = []
    for item in raw_articles:
        articles.append(
            Article(
                id=str(item["id"]),
                title=str(item["title"]),
                url=str(item.get("url", "")),
                source=str(item.get("source", "")),
                summary=str(item.get("summary", "")),
                published_date=item.get("published_date"),
            )
        )
    return articles


def _resolve_input_path(input_path: str | Path) -> Path:
    path = Path(input_path)
    if path.exists() or path.is_absolute():
        return path
    project_path = PROJECT_ROOT / path
    if project_path.exists():
        return project_path
    return path


def collect_from_rss_sources(sources_config: dict[str, Any]) -> CollectionResult:
    articles: list[Article] = []
    counts_by_source: dict[str, int] = {}
    warnings: list[str] = []

    for source in sources_config.get("sources", []):
        if source.get("type") != "rss":
            continue

        source_name = str(source.get("name", "Unknown Source"))
        url = str(source.get("url", ""))
        counts_by_source[source_name] = 0

        try:
            parsed_items = _parse_rss(url)
            max_items = int(source.get("max_items", 25))
            for index, item in enumerate(parsed_items[:max_items], start=1):
                article = normalize_rss_item(item, source_name, index)
                articles.append(article)
                counts_by_source[source_name] += 1
        except Exception as error:
            warnings.append(f"{source_name}: {error}")

    return CollectionResult(
        articles=articles,
        counts_by_source=counts_by_source,
        warnings=warnings,
    )


def normalize_rss_item(
    item: dict[str, Any],
    source_name: str,
    index: int = 1,
) -> Article:
    title = _clean_text(str(item.get("title", "")))
    url = str(item.get("link") or item.get("url") or "")
    summary = _clean_text(
        str(
            item.get("summary")
            or item.get("description")
            or item.get("content")
            or ""
        )
    )
    published_date = item.get("published") or item.get("updated") or item.get("pubDate")
    stable_id = str(item.get("id") or item.get("guid") or url or f"{source_name}-{index}")

    return Article(
        id=_article_id(source_name, stable_id, index),
        title=title,
        url=url,
        source=source_name,
        summary=summary,
        published_date=str(published_date) if published_date else None,
    )


def save_articles_json(
    articles: list[Article],
    output_path: str | Path = LATEST_RSS_PATH,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([article.__dict__ for article in articles], indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return path


def _parse_rss(url: str) -> list[dict[str, Any]]:
    try:
        import feedparser  # type: ignore

        feed = feedparser.parse(url)
        if getattr(feed, "bozo", False):
            bozo_error = getattr(feed, "bozo_exception", "malformed feed")
            raise ValueError(f"RSS parse warning: {bozo_error}")
        return [dict(entry) for entry in getattr(feed, "entries", [])]
    except ModuleNotFoundError:
        return _parse_rss_with_stdlib(url)


def _parse_rss_with_stdlib(url: str) -> list[dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=20) as response:
        body = response.read()
    root = ElementTree.fromstring(body)
    items = root.findall(".//item")
    if not items:
        items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    parsed: list[dict[str, Any]] = []
    for item in items:
        parsed.append(
            {
                "title": _node_text(item, "title"),
                "link": _node_text(item, "link") or _atom_link(item),
                "summary": _node_text(item, "description")
                or _node_text(item, "summary")
                or _node_text(item, "content"),
                "published": _node_text(item, "pubDate") or _node_text(item, "updated"),
                "id": _node_text(item, "guid") or _node_text(item, "id"),
            }
        )
    return parsed


def _node_text(item: ElementTree.Element, tag: str) -> str:
    node = item.find(tag)
    if node is None:
        node = item.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    if node is None or node.text is None:
        return ""
    return node.text


def _atom_link(item: ElementTree.Element) -> str:
    node = item.find("{http://www.w3.org/2005/Atom}link")
    if node is None:
        return ""
    return str(node.attrib.get("href", ""))


def _article_id(source_name: str, stable_id: str, index: int) -> str:
    raw = f"{source_name}-{stable_id or index}".lower()
    slug = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return slug[:120] or f"rss-{index}"


def _clean_text(value: str) -> str:
    no_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", no_tags).strip()
