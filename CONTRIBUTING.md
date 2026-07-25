# Contributing to DispoHub

Thanks for your interest in contributing! DispoHub is a young, community-run
project — contributions of all sizes are welcome, from typo fixes to new
features.

## Ground rules

- Be respectful. Assume good faith.
- Open an issue before starting large changes, so we can agree on the
  approach first and avoid wasted work.
- Keep pull requests focused — one logical change per PR is much easier to
  review than a mix of unrelated fixes.

## Development setup

```bash
git clone https://github.com/Relis-lol/dispohub.git
cd dispohub
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

See the [README](README.md) for the full installation guide, including the
Docker Compose option.

## Running tests

```bash
pytest
```

Please add or update tests for any behavior change. The test suite is the
project's main safety net — a PR that changes behavior without test coverage
is much harder to merge with confidence.

## Code style

- Python: follow the existing style in the file you're editing (the codebase
  doesn't currently enforce a formatter/linter in CI, but consistency is
  appreciated).
- Templates: this is a server-rendered Jinja2 app. New driver-facing pages
  should go through the translation system (`tr('key')`, see
  `app/i18n/translations.py`) rather than hardcoded text, so they stay
  translatable. Office/management-facing pages are currently German-only by
  design (see README "Language support").
- Database changes: add an Alembic migration (`alembic revision
  --autogenerate -m "..."`) alongside any model change, and verify it
  applies cleanly to a fresh database.

## Translations

Driver-facing strings live in `app/i18n/translations.py`, one dict per
language. The existing translations (Czech, English, Russian, Polish,
Turkish) were AI-generated and have **not** been reviewed by native
speakers — corrections from fluent/native speakers are especially welcome
and don't require any code changes beyond editing that file.

## Reporting bugs / requesting features

Please use the issue templates in `.github/ISSUE_TEMPLATE/`. The more
context you give (what you expected, what happened, how to reproduce), the
faster it can be triaged.

## Security issues

Please do **not** open a public issue for security vulnerabilities — see
[SECURITY.md](SECURITY.md) for how to report those privately.
