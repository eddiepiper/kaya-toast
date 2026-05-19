from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = PROJECT_ROOT / "reports"
DRAFTS_DIR = PROJECT_ROOT / "drafts"
INDEX_PATH = REPORTS_DIR / "INDEX.md"


def generate_report_index(index_path: str | Path = INDEX_PATH) -> Path:
    output = Path(index_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report_index(), encoding="utf-8")
    return output


def render_report_index() -> str:
    daily = _latest(REPORTS_DIR / "daily", "*-kaya-toast.md")
    weekly = _latest(REPORTS_DIR / "weekly", "*-kaya-toast-weekly.md")
    strategy = _latest(REPORTS_DIR / "strategy", "*-kaya-toast-strategy.md")
    editorial = _latest(REPORTS_DIR / "editorial", "*-kaya-toast-editorial.md")
    source_reviews = _latest_many(REPORTS_DIR / "source_review", "*-source-review.md", limit=5)
    drafts = _latest_many(DRAFTS_DIR, "*.md", limit=5)
    voice_reviews = _latest_many(REPORTS_DIR / "voice_review", "*-voice-review.md", limit=5)

    return "\n".join(
        [
            "# kaya-toast Report Index",
            "",
            "## Latest Daily Brief",
            _link_or_none(daily),
            "",
            "## Latest Editorial Recommendation",
            _link_or_none(editorial),
            "",
            "## Latest Drafts",
            _render_links(drafts),
            "## Latest Voice Reviews",
            _render_links(voice_reviews),
            "## Latest Strategy Brief",
            _link_or_none(strategy),
            "",
            "## Latest Weekly Brief",
            _link_or_none(weekly),
            "",
            "## Latest Source Reviews",
            _render_links(source_reviews),
            "## Quick Mobile Review Flow",
            "1. Read daily brief",
            "2. Read editorial recommendation",
            "3. Read draft",
            "4. Read voice review",
            "5. Give feedback later",
            "",
        ]
    )


def _latest(directory: Path, pattern: str) -> Path | None:
    paths = sorted(directory.glob(pattern)) if directory.exists() else []
    return paths[-1] if paths else None


def _latest_many(directory: Path, pattern: str, limit: int) -> list[Path]:
    paths = sorted(directory.glob(pattern)) if directory.exists() else []
    return list(reversed(paths[-limit:]))


def _link_or_none(path: Path | None) -> str:
    if path is None:
        return "None."
    return f"- [{path.name}]({_relative(path)})"


def _render_links(paths: list[Path]) -> str:
    if not paths:
        return "None.\n"
    return "\n".join(f"- [{path.name}]({_relative(path)})" for path in paths) + "\n"


def _relative(path: Path) -> str:
    return path.relative_to(REPORTS_DIR).as_posix() if path.is_relative_to(REPORTS_DIR) else f"../{path.relative_to(PROJECT_ROOT).as_posix()}"
