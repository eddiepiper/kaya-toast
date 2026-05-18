from __future__ import annotations

import argparse
from pathlib import Path

from kaya_toast.classify import classify_articles
from kaya_toast.collect import collect_from_json, collect_from_rss_sources, save_articles_json
from kaya_toast.config import load_sources
from kaya_toast.preference import SUPPORTED_RATINGS, add_feedback
from kaya_toast.recommend import recommend_articles
from kaya_toast.report import generate_report
from kaya_toast.score import score_article
from kaya_toast.workflow import run_daily, run_weekly


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaya_toast",
        description="Deterministic AI-native PM LinkedIn content idea pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run full pipeline and generate report")
    run_input = run_parser.add_mutually_exclusive_group(required=True)
    run_input.add_argument("--input", help="Path to local article JSON")
    run_input.add_argument("--rss", action="store_true", help="Collect configured RSS sources")

    classify_parser = subparsers.add_parser("classify", help="Classify local articles")
    classify_parser.add_argument("--input", required=True, help="Path to local article JSON")

    report_parser = subparsers.add_parser("report", help="Generate Markdown report")
    report_parser.add_argument("--input", required=True, help="Path to local article JSON")

    feedback_parser = subparsers.add_parser("feedback", help="Record local content idea feedback")
    feedback_parser.add_argument("--idea-id", required=True, help="Content idea ID")
    feedback_parser.add_argument("--rating", required=True, help="Feedback rating")
    feedback_parser.add_argument("--notes", default="", help="Optional feedback notes")

    subparsers.add_parser("collect-rss", help="Collect configured RSS sources")
    daily_parser = subparsers.add_parser("daily", help="Run daily RSS workflow")
    daily_parser.add_argument("--interpret", action="store_true", help="Run optional strategic interpretation")
    subparsers.add_parser("weekly", help="Generate weekly strategy brief")

    interpret_parser = subparsers.add_parser("interpret", help="Interpret a deterministic report")
    interpret_parser.add_argument("--input", required=True, help="Path to daily report")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "classify":
        articles = collect_from_json(args.input)
        classifications = classify_articles(articles)
        for article in articles:
            result = classifications[article.id]
            print(
                f"{article.id}\t{result.category}\tconfidence={result.confidence}\t"
                f"keywords={','.join(result.matched_keywords)}"
            )
        return 0

    if args.command in {"run", "report"}:
        report_path = run_pipeline(input_path=args.input, use_rss=getattr(args, "rss", False))
        print(f"Report written: {report_path}")
        return 0

    if args.command == "feedback":
        if args.rating not in SUPPORTED_RATINGS:
            allowed = ", ".join(sorted(SUPPORTED_RATINGS))
            parser.error(f"invalid rating '{args.rating}'. Supported ratings: {allowed}")
        record = add_feedback(args.idea_id, args.rating, args.notes)
        print(f"Feedback saved: {record['idea_id']} -> {record['rating']}")
        return 0

    if args.command == "collect-rss":
        result = collect_from_rss_sources(load_sources())
        output_path = save_articles_json(result.articles)
        for source, count in result.counts_by_source.items():
            print(f"{source}: {count}")
        for warning in result.warnings:
            print(f"WARNING: {warning}")
        print(f"Saved RSS articles: {output_path}")
        return 0

    if args.command == "daily":
        try:
            report_path = run_daily(interpret=args.interpret)
        except RuntimeError as error:
            print(f"Daily run failed: {error}")
            return 1
        print(f"Daily report written: {report_path}")
        return 0

    if args.command == "interpret":
        from kaya_toast.interpret import interpret_report

        result = interpret_report(args.input)
        if result.warning:
            print(f"WARNING: {result.warning}")
        else:
            print(f"Strategic interpretation written: {result.report_path}")
        return 0

    if args.command == "weekly":
        report_path = run_weekly()
        print(f"Weekly report written: {report_path}")
        return 0

    parser.print_help()
    return 0


def run_pipeline(input_path: str | Path | None = None, use_rss: bool = False) -> Path:
    source_summary = None
    if use_rss:
        collection = collect_from_rss_sources(load_sources())
        save_articles_json(collection.articles)
        articles = collection.articles
        source_summary = {
            "article_count": len(collection.articles),
            "source_names": list(collection.counts_by_source.keys()),
            "warnings": collection.warnings,
        }
        for warning in collection.warnings:
            print(f"WARNING: {warning}")
    elif input_path is not None:
        articles = collect_from_json(input_path)
        source_summary = {
            "article_count": len(articles),
            "source_names": sorted({article.source for article in articles}),
            "warnings": [],
        }
    else:
        raise ValueError("Either input_path or use_rss=True is required")

    classifications = classify_articles(articles)
    scores = {
        article.id: score_article(article, classifications[article.id])
        for article in articles
    }
    ideas = recommend_articles(articles, classifications, scores)
    return generate_report(ideas, source_summary=source_summary)
