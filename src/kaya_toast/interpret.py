from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kaya_toast.config import load_llm


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "strategic_interpretation.md"


@dataclass(frozen=True)
class InterpretationResult:
    status: str
    report_path: Path
    warning: str = ""
    interpretations: list[dict[str, str]] = field(default_factory=list)


def load_prompt_template(path: str | Path = PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


def interpret_report(
    report_path: str | Path,
    config: dict[str, Any] | None = None,
) -> InterpretationResult:
    path = Path(report_path)
    llm_config = config or load_llm()
    if not llm_config.get("enabled", False):
        return InterpretationResult(
            status="skipped",
            report_path=path,
            warning="Strategic interpretation skipped: LLM is disabled in config/llm.yaml.",
        )

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return InterpretationResult(
            status="skipped",
            report_path=path,
            warning="Strategic interpretation skipped: OPENROUTER_API_KEY is not set.",
        )

    ideas = extract_top_ideas(path)
    if not ideas:
        return InterpretationResult(
            status="skipped",
            report_path=path,
            warning="Strategic interpretation skipped: no top ideas found.",
        )

    prompt_template = load_prompt_template()
    interpretations = [
        {
            "topic": idea.get("topic", "Untitled idea"),
            "text": call_openrouter(prompt_template, idea, llm_config, api_key),
        }
        for idea in ideas[:3]
    ]
    append_interpretation_section(path, interpretations)
    return InterpretationResult(
        status="interpreted",
        report_path=path,
        interpretations=interpretations,
    )


def extract_top_ideas(report_path: str | Path) -> list[dict[str, str]]:
    ideas: list[dict[str, str]] = []
    in_top_section = False
    current: dict[str, str] | None = None

    for line in Path(report_path).read_text(encoding="utf-8").splitlines():
        if line == "## Top LinkedIn Content Ideas":
            in_top_section = True
            continue
        if in_top_section and line.startswith("## "):
            break
        if not in_top_section:
            continue
        if line.startswith("### "):
            if current:
                ideas.append(current)
            current = {"topic": line.removeprefix("### ").strip()}
        elif current is not None and line.startswith("- "):
            key, _, value = line.removeprefix("- ").partition(": ")
            if key and value:
                current[key.lower().replace(" ", "_")] = value.strip()

    if current:
        ideas.append(current)
    return ideas


def append_interpretation_section(
    report_path: str | Path,
    interpretations: list[dict[str, str]],
) -> None:
    path = Path(report_path)
    text = path.read_text(encoding="utf-8")
    if "## Strategic Interpretation" in text:
        text = text.split("## Strategic Interpretation", 1)[0].rstrip() + "\n"

    section = ["", "## Strategic Interpretation", ""]
    for item in interpretations:
        section.extend(
            [
                f"### {item['topic']}",
                "",
                item["text"].strip(),
                "",
            ]
        )
    path.write_text(text.rstrip() + "\n" + "\n".join(section).rstrip() + "\n", encoding="utf-8")


def call_openrouter(
    prompt_template: str,
    idea: dict[str, str],
    config: dict[str, Any],
    api_key: str,
) -> str:
    payload = {
        "model": config["model"],
        "temperature": config.get("temperature", 0.3),
        "max_tokens": config.get("max_tokens", 1200),
        "messages": [
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": json.dumps(idea, indent=2, sort_keys=True)},
        ],
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.kaya-toast",
            "X-Title": "kaya-toast",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return str(data["choices"][0]["message"]["content"]).strip()
