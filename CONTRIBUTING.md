# Contributing

The short version: **bug reports are welcome; code contributions are not being sought.**

FIREMaster is a personal tool, published so that the people running it can audit what
touches their financial data. It is built and maintained by one person, for his own
retirement first. It is not a community project, and this file is here so nobody has to
discover that through an awkward PR review.

## Bug reports — yes

If something is broken, an issue with reproduction steps is genuinely appreciated:

- What you did, what you expected, what happened instead
- Container or native path, OS, and the relevant log lines
  (`docker compose logs backend` usually has the story)
- For projection/engine questions: the config values involved (never post real account
  data — see below)

There is **no SLA**. Issues get read; fixes happen when they happen.

## Pull requests — closed by default

Please open an issue *before* writing any code. Unsolicited PRs will generally be closed
unread, regardless of quality — not out of disrespect, but because:

- Every merged line becomes a maintenance obligation on one person
- The engine encodes deliberate financial-modeling decisions that look like bugs until
  they aren't (see `ARCHITECTURE.md`)
- Keeping the copyright uniform preserves the project's licensing freedom

If an issue discussion ends with "a PR for this would be accepted," that's the invitation.
Anything merged requires agreement that the contribution is licensed to the project's
copyright holder.

## Feature requests

You can file them, with expectations set accordingly: the roadmap is whatever the author
needs next. The good news is that the API-first design means many "features" don't need
code — point Claude Code (or any agent) at the backend API and ask your question. That's
the intended extension mechanism.

## One hard rule

**Never post real financial data** — account numbers, balances, institution names tied to
amounts, transaction exports — in issues, PRs, or discussions. Redact first. Reports
containing PII may be deleted outright to keep it out of search indexes.

## Security issues

Not here — see [SECURITY.md](SECURITY.md) for the private disclosure route.
