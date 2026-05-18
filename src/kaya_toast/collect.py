from __future__ import annotations

import json
from pathlib import Path

from kaya_toast.models import Article


def collect_from_json(input_path: str | Path) -> list[Article]:
    path = Path(input_path)
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
