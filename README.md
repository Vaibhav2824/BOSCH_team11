# Incident Zero (BOSCH team 11)

AI on-call engineer for the OpenTelemetry Astronomy Shop: detect, investigate, diagnose,
propose, get approval, act and verify, report.

## Dev setup

```bash
uv sync
cp .env.example .env   # add your own GROQ_API_KEY
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Code lives in `src/oncall/`. Each file has one owner (see the docstring at its top);
message the owner before editing someone else's file. `git pull --rebase` before every push.

Sections still to write: Setup / How to run (A), Approval gate and kill switch (D),
known limitations.
