from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from kaya_toast.classify import classify_articles
from kaya_toast.collect import (
    LATEST_RSS_PATH,
    CollectionResult,
    collect_from_json,
    collect_from_rss_sources,
    save_articles_json,
)
from kaya_toast.config import load_sources
from kaya_toast.models import Article, ContentIdea
from kaya_toast.pillars import filter_by_pillar
from kaya_toast.recommend import recommend_articles
from kaya_toast.report import generate_report
from kaya_toast.score import score_article


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_HISTORY_PATH = PROJECT_ROOT / "data" / "run_history.json"
DAILY_REPORTS_DIR = PROJECT_ROOT / "reports" / "daily"
WEEKLY_REPORTS_DIR = PROJECT_ROOT / "reports" / "weekly"


def build_ideas(articles: list[Article]) -> list[ContentIdea]:
    classifications = classify_articles(articles)
    scores = {
        article.id: score_article(article, classifications[article.id])
        for article in articles
    }
    return recommend_articles(articles, classifications, scores)


def run_daily(interpret: bool = False, pillar: str = "ai_native_pm") -> Path:
    collection = collect_from_rss_sources(load_sources())
    articles = collection.articles
    warnings = list(collection.warnings)
    source_names = list(collection.counts_by_source.keys())

    if articles:
        save_articles_json(articles)
    elif LATEST_RSS_PATH.exists():
        articles = collect_from_json(LATEST_RSS_PATH)
        warnings.append(
            f"RSS collection returned no articles; used fallback {LATEST_RSS_PATH}"
        )
        source_names = sorted({article.source for article in articles})
    else:
        raise RuntimeError(
            "RSS collection returned no articles and no fallback exists at "
            f"{LATEST_RSS_PATH}"
        )

    ideas = filter_by_pillar(build_ideas(articles), pillar)
    source_summary = {
        "article_count": len(articles),
        "source_names": source_names,
        "warnings": warnings,
    }
    report_path = generate_report(
        ideas,
        reports_dir=DAILY_REPORTS_DIR,
        source_summary=source_summary,
    )
    append_run_history(
        articles_collected=len(articles),
        ideas_generated=len(ideas),
        report_path=report_path,
        warnings=warnings,
    )
    if interpret:
        from kaya_toast.interpret import interpret_report

        result = interpret_report(report_path)
        if result.warning:
            print(f"WARNING: {result.warning}")
    return report_path


def append_run_history(
    articles_collected: int,
    ideas_generated: int,
    report_path: str | Path,
    warnings: list[str],
    path: str | Path | None = None,
) -> dict:
    history_path = Path(path) if path is not None else RUN_HISTORY_PATH
    history_path.parent.mkdir(parents=True, exist_ok=True)
    records = load_run_history(history_path)
    timestamp = datetime.now(timezone.utc).isoformat()
    record = {
        "run_id": f"daily-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "timestamp": timestamp,
        "articles_collected": articles_collected,
        "ideas_generated": ideas_generated,
        "report_path": str(report_path),
        "warnings": warnings,
    }
    records.append(record)
    history_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record


def load_run_history(path: str | Path = RUN_HISTORY_PATH) -> list[dict]:
    history_path = Path(path)
    if not history_path.exists():
        return []
    with history_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError(f"Run history must contain a list: {history_path}")
    return data


def run_weekly() -> Path:
    daily_reports = _recent_daily_reports(DAILY_REPORTS_DIR)
    WEEKLY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    weekly_path = WEEKLY_REPORTS_DIR / f"{date.today().isoformat()}-kaya-toast-weekly.md"
    weekly_path.write_text(render_weekly_report(daily_reports), encoding="utf-8")
    return weekly_path


def render_weekly_report(daily_reports: list[Path]) -> str:
    ideas = _extract_ideas_from_reports(daily_reports)
    best_ideas = ideas[:3]
    categories = _count_field(ideas, "category")
    fluff_patterns = _extract_fluff_patterns(daily_reports)

    sections = [
        "# kaya-toast Weekly Strategy Brief",
        "",
        "## Best 3 LinkedIn Ideas This Week",
        "",
        _render_weekly_ideas(best_ideas),
        "## Emerging Themes",
        "",
        _render_list([f"{category}: {count} ideas" for category, count in categories[:5]]),
        "## Topics to Avoid",
        "",
        _render_list(_topics_to_avoid(ideas)),
        "## Fluff Patterns Detected",
        "",
        _render_list(fluff_patterns),
        "## Preference Memory Update",
        "",
        "- Review this week's highest scoring categories against recent feedback before drafting.",
        "",
        "## Recommended Posting Plan",
        "",
        "- Monday: strategic AI-native PM shift",
        "- Wednesday: practical workflow or operator lesson",
        "- Friday: industry signal or contrarian take",
    ]
    return "\n".join(sections).rstrip() + "\n"


def _recent_daily_reports(reports_dir: Path) -> list[Path]:
    if not reports_dir.exists():
        return []
    cutoff = date.today() - timedelta(days=6)
    reports: list[Path] = []
    for report in sorted(reports_dir.glob("*-kaya-toast.md"), reverse=True):
        report_date = _date_from_report_name(report.name)
        if report_date and report_date >= cutoff:
            reports.append(report)
    return sorted(reports)


def _date_from_report_name(name: str) -> date | None:
    match = re.match(r"(\d{4}-\d{2}-\d{2})-kaya-toast\.md$", name)
    if not match:
        return None
    return date.fromisoformat(match.group(1))


def _extract_ideas_from_reports(paths: list[Path]) -> list[dict]:
    ideas: list[dict] = []
    for path in paths:
        current: dict[str, str | list[str]] | None = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                if current:
                    ideas.append(current)
                current = {"topic": line.removeprefix("### ").strip(), "hooks": []}
            elif current is not None and line.startswith("- Category: "):
                current["category"] = line.removeprefix("- Category: ").strip()
            elif current is not None and line.startswith("- Why it matters: "):
                current["why"] = line.removeprefix("- Why it matters: ").strip()
            elif current is not None and line.startswith("- Suggested angle: "):
                current["angle"] = line.removeprefix("- Suggested angle: ").strip()
            elif current is not None and line.startswith("- Final Score: "):
                current["score"] = line.removeprefix("- Final Score: ").strip()
            elif current is not None and line.startswith("- Preference Adjustment: "):
                current["preference"] = line.removeprefix("- Preference Adjustment: ").strip()
            elif current is not None and line.strip().startswith("- ") and "hooks" in current:
                hook = line.strip().removeprefix("- ").strip()
                if hook and not hook.startswith(
                    (
                        "Hook options:",
                        "Topic:",
                        "Category:",
                        "Source:",
                        "Why",
                        "Target",
                        "Suggested",
                        "Score:",
                        "Fluff",
                        "Recommendation",
                        "Idea ID",
                        "Preference",
                        "Final",
                    )
                ):
                    current["hooks"].append(hook)
        if current:
            ideas.append(current)
    return sorted(ideas, key=lambda idea: int(str(idea.get("score", "0"))), reverse=True)


def _render_weekly_ideas(ideas: list[dict]) -> str:
    if not ideas:
        return "None.\n"
    blocks = []
    for idea in ideas:
        hooks = idea.get("hooks", [])
        hook_lines = "\n".join(f"  - {hook}" for hook in hooks) if hooks else "  - None"
        blocks.append(
            "\n".join(
                [
                    f"### {idea.get('topic', 'Untitled idea')}",
                    "",
                    f"- Topic: {idea.get('topic', 'Untitled idea')}",
                    f"- Category: {idea.get('category', 'uncategorized')}",
                    f"- Why it matters: {idea.get('why', 'Not captured in daily report.')}",
                    f"- Suggested angle: {idea.get('angle', 'Not captured in daily report.')}",
                    "- Hook options:",
                    hook_lines,
                    f"- Score: {idea.get('score', '0')}",
                    f"- Preference match: {idea.get('preference', '0')}",
                    "",
                ]
            )
        )
    return "\n".join(blocks)


def _count_field(ideas: list[dict], field: str) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for idea in ideas:
        value = str(idea.get(field, "")).strip()
        if value:
            counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)


def _topics_to_avoid(ideas: list[dict]) -> list[str]:
    low_signal = [
        str(idea.get("topic", ""))
        for idea in ideas
        if int(str(idea.get("score", "0"))) < 50
    ]
    return low_signal[:5]


def _extract_fluff_patterns(paths: list[Path]) -> list[str]:
    patterns: list[str] = []
    for path in paths:
        in_fluff = False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line == "## Fluff Warnings":
                in_fluff = True
                continue
            if in_fluff and line.startswith("## "):
                in_fluff = False
            if in_fluff and line.startswith("- ") and line != "- None":
                patterns.append(line.removeprefix("- ").strip())
    return patterns[:5]


def _render_list(items: list[str]) -> str:
    if not items:
        return "None.\n"
    return "\n".join(f"- {item}" for item in items) + "\n"
