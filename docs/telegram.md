# kaya-toast Telegram Review Agent

The Telegram review layer is command-only and safe by default. It reads the latest daily report, maps numbered ideas to idea IDs, and can generate drafts or voice reviews only when explicitly requested.

Supported commands:

- `/top`
- `/idea 1`
- `/like 1`
- `/use_later 1`
- `/too_generic 1`
- `/strong_angle 1`
- `/draft 1`
- `/voice_review 1`
- `/help`

Configuration:

- Token is read only from `TELEGRAM_BOT_TOKEN`.
- No token is stored in the repo.
- Missing token must not break dry-run validation.
- LinkedIn auto-posting is not supported.

Local dry run:

```bash
python3 -m kaya_toast telegram-review --dry-run /top
python3 -m kaya_toast telegram-review --dry-run "/idea 1"
```
