# kaya-toast

`kaya-toast` is a local-first, deterministic MVP for recommending high-signal LinkedIn content ideas about AI-native Product Management.

It helps traditional Product Managers transition into AI-native PMs through practical, strategic, enterprise-aware content ideas. Phase 1 and Phase 2 do not generate full LinkedIn posts, call external APIs, scrape the web, schedule jobs, or post to LinkedIn.

## What It Does

Pipeline:

```text
collect -> classify -> score -> fluff_check -> recommend -> report
```

Inputs are local JSON article summaries. Outputs are ranked Markdown briefings with post, park, and reject recommendations.

## Setup

```bash
python -m pip install -e ".[dev]"
```

## CLI

```bash
python -m kaya_toast --help
python -m kaya_toast run --input examples/sample_articles.json
python -m kaya_toast classify --input examples/sample_articles.json
python -m kaya_toast report --input examples/sample_articles.json
python -m kaya_toast feedback --idea-id "context_engineering::context-engineering-is-becoming-a-pm-operating-skill" --rating like
```

## Test

```bash
python -m pytest -q
```

## Current Scope

Included:

- Local JSON collection
- Deterministic classification
- Deterministic scoring
- Fluff detection
- Local preference feedback
- Content idea templating
- Markdown reporting
- Tests

## Feedback Loop

Feedback is stored locally in `data/feedback.json`.

Supported ratings:

- `like`
- `dislike`
- `use_later`
- `too_fluffy`
- `too_generic`
- `too_technical`
- `strong_angle`
- `weak_angle`

Rate the `Idea ID` shown in the Markdown report for future preference adjustments.

Excluded:

- Web UI
- Vector database
- Multi-agent orchestration
- LangChain, CrewAI, AutoGen
- LinkedIn posting
- External APIs
- Browser scraping
- Cron scheduling
- Database
- Full LinkedIn post generation
