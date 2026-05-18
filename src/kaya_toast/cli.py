from __future__ import annotations

import argparse
from pathlib import Path

from kaya_toast.classify import classify_articles
from kaya_toast.collect import collect_from_json
from kaya_toast.preference import SUPPORTED_RATINGS, add_feedback
from kaya_toast.recommend import recommend_articles
from kaya_toast.report import generate_report
from kaya_toast.score import score_article


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaya_toast",
        description="Deterministic AI-native PM LinkedIn content idea pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run full pipeline and generate report")
    run_parser.add_argument("--input", required=True, help="Path to local article JSON")

    classify_parser = subparsers.add_parser("classify", help="Classify local articles")
    classify_parser.add_argument("--input", required=True, help="Path to local article JSON")

    report_parser = subparsers.add_parser("report", help="Generate Markdown report")
    report_parser.add_argument("--input", required=True, help="Path to local article JSON")

    feedback_parser = subparsers.add_parser("feedback", help="Record local content idea feedback")
    feedback_parser.add_argument("--idea-id", required=True, help="Content idea ID")
    feedback_parser.add_argument("--rating", required=True, help="Feedback rating")
    feedback_parser.add_argument("--notes", default="", help="Optional feedback notes")

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
        report_path = run_pipeline(args.input)
        print(f"Report written: {report_path}")
        return 0

    if args.command == "feedback":
        if args.rating not in SUPPORTED_RATINGS:
            allowed = ", ".join(sorted(SUPPORTED_RATINGS))
            parser.error(f"invalid rating '{args.rating}'. Supported ratings: {allowed}")
        record = add_feedback(args.idea_id, args.rating, args.notes)
        print(f"Feedback saved: {record['idea_id']} -> {record['rating']}")
        return 0

    parser.print_help()
    return 0


def run_pipeline(input_path: str | Path) -> Path:
    articles = collect_from_json(input_path)
    classifications = classify_articles(articles)
    scores = {
        article.id: score_article(article, classifications[article.id])
        for article in articles
    }
    ideas = recommend_articles(articles, classifications, scores)
    return generate_report(ideas)
