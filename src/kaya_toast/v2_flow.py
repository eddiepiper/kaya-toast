from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kaya_toast.draft import draft_from_report
from kaya_toast.editorial import generate_editorial_report
from kaya_toast.report_index import generate_report_index
from kaya_toast.source_review import generate_source_reviews
from kaya_toast.voice_review import generate_all_latest_voice_reviews
from kaya_toast.workflow import run_daily


@dataclass(frozen=True)
class V2FlowResult:
    daily_report: Path
    editorial_report: Path
    source_review_reports: list[Path]
    draft_files: list[Path]
    voice_review_reports: list[Path]
    index_path: Path


def run_v2_flow(top: int = 3) -> V2FlowResult:
    daily_report = run_daily()
    editorial_report = generate_editorial_report(daily_report)
    source_reviews = generate_source_reviews(daily_report, top=top)
    drafts = draft_from_report(daily_report, top=top, use_source_review=True)
    voice_reviews = generate_all_latest_voice_reviews()
    index_path = generate_report_index()
    return V2FlowResult(
        daily_report=daily_report,
        editorial_report=editorial_report,
        source_review_reports=source_reviews,
        draft_files=drafts,
        voice_review_reports=voice_reviews,
        index_path=index_path,
    )


def render_v2_flow_result(result: V2FlowResult) -> str:
    lines = [
        f"Daily report: {result.daily_report}",
        f"Editorial report: {result.editorial_report}",
        "Source review reports:",
        *_render_paths(result.source_review_reports),
        "Draft files:",
        *_render_paths(result.draft_files),
        "Voice review reports:",
        *_render_paths(result.voice_review_reports),
        f"Report index: {result.index_path}",
    ]
    return "\n".join(lines)


def _render_paths(paths: list[Path]) -> list[str]:
    return [f"- {path}" for path in paths] or ["- None"]
