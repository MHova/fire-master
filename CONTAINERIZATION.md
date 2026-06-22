# Containerization Plan — making FIREMaster easy to install

> **Why this document exists.** FIREMaster was built on macOS and assumes a Unix
> toolchain. Installing it on a clean Windows machine (this test) currently requires
> **six tools and a Linux shell** before the app will run. This document explains why,
> and lays out a plan to get the install down to **two prerequisites (Docker + Git) and
> one command** on every operating system.
>
> It is written for someone **new to Docker.** Part 1 teaches the concepts using *this*
> app as the example. Part 2 diagnoses where we are today. Part 3 is the concrete plan.
> If you already know Docker, skip to Part 2.

---

## Part 1 — Docker concepts, explained with FIREMaster

### The problem containers solve

FIREMaster is not one program. It's **five cooperating programs**:

| Piece | What it is | Needs |
|---|---|---|
| PostgreSQL | The database (stores accounts, transactions) | Postgres 16 |
| Redis | A fast in-memory store / message queue | Redis 7 |
| Backend API | Your FastAPI app (the real product) | Python 3.12 + `uv` + libs |
| Celery worker | Background jobs (Monarch sync, reclassify) | same as backend |
| Celery beat | A scheduler that triggers the worker on a timer | same as backend |
| Frontend | The React dashboard you view in the browser | Node + npm |

Without containers, a user has to install **all** of those runtimes on their own machine,
in the right versions, and make them find each other. That's the gauntlet — on Windows it
also means there's no Postgres, no Redis, no Python 3.12, no Node by default.

### What a container is

A **container** is a sealed box that holds *one* of those programs **plus everything it
needs to run** — the right OS libraries, the right language version, the right
dependencies. You don't install Python or Postgres on your machine; the container already
has them inside. Your machine only needs **Docker** (the thing that runs boxes).

Think of it as: instead of giving a user a recipe ("first install Python 3.12, then
Postgres 16, then…"), you give them the **finished meal, sealed**. Same meal on every
machine.

### Image vs. container

- An **image** is the recipe/blueprint — a frozen, shareable snapshot of "Postgres 16 set
  up just so." Images have names like `postgres:16-alpine`.
- A **container** is a *running instance* of an image — the box actually turned on.

You build or download an image once; you can start/stop containers from it as often as you
like. (Analogy: image = a class, container = an object. Or image = an `.iso`, container =
the booted machine.)

### The Dockerfile — how an image gets built

A **`Dockerfile`** is the script that *builds* an image: "start from Python 3.12, install
these libraries, copy in the code, here's the command to run." You already have one at
[backend/Dockerfile](backend/Dockerfile) — that's why the backend is already half-solved.

### Docker Compose — running the five boxes together

A single app made of five containers needs them wired together: the backend has to find
the database, the worker has to find Redis, ports have to be exposed to your browser.

**Docker Compose** is the tool for that. One file, [docker-compose.yml](docker-compose.yml),
describes all the services, and a single command —

```bash
docker compose up
```

— starts the whole fleet, in the right order, on a private network where they can find
each other **by name**. This is the key idea for the plan below: *Compose can replace the
hand-written `start.sh` orchestration script entirely, and it works identically on Mac,
Windows, and Linux.*

### The one piece of jargon that bites us: networking

When containers run under Compose, they talk to each other using **service names** as
hostnames, not `localhost`.

- Inside the `backend` container, the database is reachable at **`postgres:5432`** —
  because the service is named `postgres` in the compose file.
- **`localhost` inside a container means "this container itself"** — *not* your machine
  and *not* another container.

Remember this sentence; it's the root of the bug in Part 2.

---

## Part 2 — Where FIREMaster is today

### What's already containerized ✅

The backend is done well: [backend/Dockerfile](backend/Dockerfile) builds a Python 3.12
image, installs `uv`, installs dependencies, copies the code. The
[docker-compose.yml](docker-compose.yml) already defines `postgres`, `redis`, `backend`,
`celery-worker`, and `celery-beat` services.

### What's NOT containerized ❌

1. **The frontend.** There is no `frontend/Dockerfile`. The React app runs on the *host*
   via `npm run dev`, launched by [scripts/start.sh](scripts/start.sh). → This is why a
   user must install **Node**.

2. **The orchestration is a bash script, not Compose.** [scripts/start.sh](scripts/start.sh)
   is what users actually run, and it:
   - kills stale processes with `lsof` (Unix-only — doesn't exist on Windows),
   - runs `docker compose up` for *only* postgres + redis,
   - then runs the backend, Celery, and frontend **on the host** with `uv`/`npm`,
   - manages process IDs and cleanup with `trap` (Unix-only).
   → This is why a user must install **`uv`, Node, and a bash shell** even though Docker
   is right there.

3. **Setup is a bash script too.** [scripts/setup.sh](scripts/setup.sh) generates a JWT
   secret with `openssl`, reads a password, hashes it with bcrypt via `uv`, and edits the
   `.env` file with `sed`. Every one of those (`openssl`, `read -s`, `uv`, `sed`, bash) is
   a Unix dependency. → This is the very first thing a user runs, and it can't run on
   Windows without a Unix shell.

### The latent bug 🐞 (two conflicting run-modes)

Your [.env.example](.env.example) sets:

```
DATABASE_URL=postgresql+asyncpg://firemaster:firemaster@localhost:5432/firemaster
REDIS_URL=redis://localhost:6379/0
```

Those `localhost` values are correct for **`start.sh` mode**, where the backend runs on the
*host* and reaches Postgres through a published port. **But** the same `.env` is fed to the
`backend`/`celery` **containers** in [docker-compose.yml](docker-compose.yml) — and as we
learned in Part 1, `localhost` *inside* the backend container is the container itself, not
Postgres. So:

- **`start.sh` mode** (backend on host): works.
- **Full `docker compose up` mode** (backend in a container): the backend can't find the
  database — it would need `@postgres:5432` and `redis:6379`.

In other words, the "just run `docker compose up`" path that *should* be the easy button is
currently broken/untested. There are effectively two run-modes and only the harder one
works. Fixing this is the heart of the plan.

### The net effect on a Windows user

Today's required install (what this test proved):

```
git  +  gh  +  Docker Desktop  +  uv  +  Node  +  WSL2/Ubuntu  +  a bash shell
```

…then run bash scripts that use `lsof`, `openssl`, `sed`, `trap`. That's the "overwhelming."

---

## Part 3 — The plan: `docker compose up` and nothing else

**Goal:** any user, any OS, needs only **Docker Desktop + Git**, then:

```bash
git clone https://github.com/gdb-mtx/fire-master && cd fire-master
docker compose up
# open http://localhost:5173
```

No `uv`, no Node, no bash scripts, no Ubuntu distro to manage. Here are the changes, in
recommended order. Each is independent enough to do and test on its own.

### Change 1 — Fix the networking so full-Docker mode works *(fixes the bug; do this first)*

- Point the backend/worker at the **service names**, not `localhost`:
  `@postgres:5432` and `redis:6379`.
- Keep a way to override for host-based dev (e.g. a separate `.env` or a compose
  `environment:` override), so the contributor workflow still works.
- **Test:** `docker compose up` and confirm the backend logs show a successful DB
  connection instead of a connection-refused error.

*Why first: nothing else in full-Docker mode works until this is right, and it's small.*

### Change 2 — Containerize the frontend *(removes Node from the host)*

- Add a `frontend/Dockerfile`. For development, the simplest version installs deps and runs
  Vite's dev server; for a shareable build, a two-stage Dockerfile builds the static site
  and serves it with a tiny web server (nginx).
- Add a `frontend` service to [docker-compose.yml](docker-compose.yml) exposing port 5173
  (dev) or 80 (prod build).
- **Test:** `docker compose up` then open `http://localhost:5173` — dashboard loads with no
  Node installed on the host.

### Change 3 — Run database migrations automatically on startup *(removes a manual step + host `uv`)*

- Today a human runs `uv run alembic upgrade head`. Move it into the backend container's
  startup (an entrypoint script that runs migrations, then launches uvicorn), so the DB
  schema is always created/updated when the stack comes up.
- **Test:** delete the database volume, `docker compose up`, confirm tables get created
  with no manual command.

### Change 4 — Replace `setup.sh` with a cross-platform setup *(removes `openssl`/`sed`/`read`/bash)*

Two options (we can pick together):

- **(a) Auto-generate on first boot** — if no JWT secret / admin password exists, the
  backend generates a random secret and creates a default admin, printing the credentials
  to the log. Zero commands for the user.
- **(b) A one-liner setup command** — `docker compose run --rm backend python -m app.setup`
  prompts for a password and writes the secrets. Uses the Python + bcrypt already inside
  the image; no host tools.

**Test:** on a clean checkout with no `.env`, the user can reach a working login without
running any bash.

### Change 5 — Retire `start.sh` as the *user* path *(removes the bash/`lsof`/`trap` dependency)*

- Once Changes 1–4 land, `docker compose up` does everything `start.sh` did — lifecycle,
  health checks, restart-on-crash — identically on every OS.
- Keep `start.sh`/`setup.sh` only as an **optional contributor convenience** for native
  Mac/Linux development (running the backend outside a container for fast reloads), clearly
  labeled as such — not the documented user path.

### Change 6 — Publish prebuilt, multi-architecture images *(polish; optional but high-value)*

- Build images for **both** `amd64` (Intel/AMD) and `arm64` (Apple Silicon, your Windows-ARM
  VM, Raspberry Pi) and push them to **GHCR** (GitHub Container Registry) via a GitHub
  Action — the GitHub Actions extension you installed is exactly for editing that workflow.
- Then the compose file can `pull` finished images instead of `build`-ing them locally, so
  users skip the slow first-time build and architecture mismatches.
- **Test:** on a fresh machine, `docker compose pull && docker compose up` with no local
  build step.

### Change 7 — Documentation to match *(removes the "I had no idea" factor)*

- Rewrite the README Quick Start around `docker compose up`.
- Add `docs/WINDOWS.md`: install Docker Desktop (it sets up WSL2 itself), install Git,
  clone, `docker compose up`. Set the expectation honestly: one reboot during Docker
  Desktop's WSL2 setup, then two commands.
- Drop `gh` from the user path entirely once the repo is public or ships a release tarball —
  users should never authenticate anything to *use* the app.

---

## Part 3.5 — Effect on the dual-interface (the copilot)

A core worry: does containerizing break the "copilot" — Claude Code reading your data and
**writing its own scenarios into the app** ([docs/CLAUDE_CODE_USAGE.md](docs/CLAUDE_CODE_USAGE.md))?

**Short answer: no.** The copilot works over **HTTP against `localhost:8000`** — auth via
`POST /api/auth/login`, reads via `GET …`, and scenario writes via
`POST /api/fire/scenarios` / `PUT /api/fire/scenarios/{id}` / `POST …/activate`
([backend/app/api/fire.py](backend/app/api/fire.py)). Because compose **publishes** the
backend port (`ports: "8000:8000"`), a containerized backend is *indistinguishable from a
host backend* to any API client. CORS doesn't apply (not a browser); JWT is unchanged. The
teaching file [CLAUDE.md](CLAUDE.md) is just a repo file on disk — containerizing the
*runtime* doesn't move your *source*, so Claude still reads it and still writes `reports/`
artifacts to the repo. **The only thing that changes is running repo *scripts*** (seeding,
migrations, reports) — those move from `uv run python …` on the host to
`docker compose run/exec … python …` inside the container.

That script change has a few sharp edges the plan MUST handle:

1. **🐞 Scripts and config aren't in the container yet.** The Dockerfile builds from the
   `./backend` context and compose mounts only `./backend:/app/backend`, but `scripts/` and
   `config/` live at the **repo root** — so `docker compose run --rm backend python
   ../scripts/seed_demo.py` fails ("file not found"). **Fix:** mount the repo root (or a
   `scripts/`+`config/` mount), or move those folders under `backend/`, or add a small
   `tasks` service that mounts the root. Without this, in-container script runs don't work.
2. **Outputs can vanish with `--rm`.** A throwaway container deletes anything written to a
   non-mounted path. Claude's `reports/` are written by Claude itself (host file I/O) so
   they're safe; a *script* that exports a file needs its output path on a mounted volume.
   (Same fix as #1.)
3. **Interactive/stateful scripts.** `monarch_login.py` needs a TTY (MFA prompt) and writes
   the Monarch **session file** that the celery-worker later reads — both must see the same
   file. Today `MONARCH_SESSION_FILE=.monarch_session` is under `backend/` (mounted into
   every service), so this works — but test it after the change.
4. **Startup overhead.** `docker compose run` creates a fresh container each call (seconds);
   prefer `docker compose exec backend …` against the already-running stack for repeated
   commands.
5. **Contributor test loop.** `cd backend && uv run pytest` becomes
   `docker compose run --rm backend uv run pytest` unless a dev keeps `uv` on the host — a
   contributor convenience, not a user concern (another reason to keep the native dev path).

**Net:** the copilot's day-to-day (API calls) is unaffected; the script path needs item #1
fixed and #2–#4 handled with the same mount + sensible defaults.

## What's still irreducible on Windows

Even after all of this, **Docker Desktop on Windows needs WSL2 underneath**, and enabling
WSL2 requires **one reboot**. The crucial difference: **Docker Desktop's own installer does
that for the user.** They never install or manage an Ubuntu distro, never touch `uv`, Node,
or bash. It becomes "run Docker's installer, reboot once, then two commands" — which is a
normal, well-trodden Windows setup, not a research project.

---

## Suggested order of work

```
Change 1 (networking fix)      ← unblocks everything, smallest
Change 2 (frontend container)  ← removes Node
Change 3 (auto-migrations)     ← removes a manual step + host uv
Change 4 (cross-platform setup)← removes the bash setup script
Change 5 (retire start.sh)     ← the payoff: compose-only
Change 6 (prebuilt images)     ← polish, optional
Change 7 (docs)                ← do alongside, finish last
```

After Changes 1–5, re-run *this* Windows test: it should collapse from the six-tool
gauntlet to "install Docker Desktop, install Git, clone, `docker compose up`." That
re-test is the proof the plan worked.
