# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

A personal, private game library journal built with Flask (Python). The app has two core sections:

- **Active Library** — track games currently being played, with per-game enjoyment ratings, motivation-to-finish ratings, status tracking, and freeform notes
- **Backlog Manager** — organize unplayed games by user-defined categories, ranked by priority via drag-and-drop, with a one-click promote-to-active flow

Access is restricted entirely by Tailscale — no login system exists. If you're on the Tailnet, you can access the app. The app binds to the server's Tailscale IP only.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3 |
| Web Framework | Flask |
| ORM | Flask-SQLAlchemy |
| Database Driver | PyMySQL |
| Database | MySQL (pre-existing server instance) |
| Templates | Jinja2 (built into Flask) |
| Styling | Tailwind CSS (CDN) |
| Drag-and-Drop | SortableJS (CDN) |
| Production Server | Gunicorn |
| Environment Vars | python-dotenv |
| Network / Auth | Tailscale |
| Game Metadata API | RAWG (rawg.io) |

---

## Project Status

Phases 1–5 complete. Core app is functional end-to-end.

**Completed:**
1. ✅ Project scaffolding and virtual environment
2. ✅ Database schema design and SQLAlchemy models
3. ✅ MySQL connection, table generation, and seed data
4. ✅ Tailscale network binding
5. ✅ Flask Blueprints, full CRUD routes, and all views

**Remaining:**
6. Error handling and responsive layout polish
7. Gunicorn + systemd deployment on Tailscale-bound IP

---

## Project Structure

```
game-journal/
├── app/
│   ├── __init__.py          # App factory — db init, blueprint + CLI registration
│   ├── models.py            # SQLAlchemy models: Game, Category
│   ├── seeds.py             # flask seed CLI command
│   ├── blueprints/
│   │   ├── main.py          # Dashboard (/) and RAWG search proxy (/api/games/search)
│   │   ├── playing.py       # Active library routes (/playing)
│   │   └── backlog.py       # Backlog routes (/backlog)
│   ├── utils/
│   │   └── rawg.py          # RAWG API helpers: search_games(), get_game(), extract_metadata()
│   ├── templates/
│   │   ├── base.html        # Base Jinja2 template with nav, Tailwind + SortableJS CDN
│   │   ├── main/
│   │   │   └── index.html   # Dashboard — stat cards + top backlog
│   │   ├── playing/
│   │   │   ├── index.html   # Active library card grid
│   │   │   ├── detail.html  # Per-game status page
│   │   │   └── form.html    # Shared add/edit form (RAWG search + star ratings)
│   │   └── backlog/
│   │       ├── index.html   # Sortable category groups
│   │       ├── add.html     # Add to backlog (RAWG search + category picker)
│   │       └── categories.html
│   └── static/
├── .env                     # Never commit — see .env.example
├── .env.example
├── .gitignore
├── config.py                # DevelopmentConfig / ProductionConfig
├── requirements.txt
└── run.py                   # Dev entry point — binds to TAILSCALE_IP
```

---

## Setup

**Virtual environment:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Environment variables — copy and fill in `.env`:**
```
FLASK_SECRET_KEY=any-random-string
DATABASE_URL=mysql+pymysql://user:password@host/dbname
FLASK_ENV=development
RAWG_API_KEY=your-rawg-api-key        # from rawg.io/apidocs — free account
TAILSCALE_IP=100.x.x.x                # from: tailscale ip -4
PORT=5000
```

**Initialize the database:**
```bash
flask shell
>>> from app import db, models   # models import is required — see Gotchas
>>> db.create_all()
```

**Seed with example data (fetches cover art from RAWG if key is set):**
```bash
flask seed
```

**Run (binds to TAILSCALE_IP if set, otherwise 127.0.0.1):**
```bash
python run.py
```

---

## Database Models

### `Category`
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key, autoincrement |
| name | String(100) | User-defined label |

**Relationship:** `category.games` → ordered by `rank ASC` automatically.

### `Game`
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key, autoincrement |
| name | String(200) | Required |
| section | Enum | `'active'` or `'backlog'` |
| status | Enum | `'Playing'`, `'On Hold'`, `'Dropped'`, `'Completed'` — nullable |
| enjoyment | Integer | 1–5, nullable |
| motivation | Integer | 1–5, nullable |
| notes | Text | Freeform, nullable |
| rank | Integer | Backlog priority within category, default 0, NOT NULL |
| category_id | ForeignKey | `categories.id` ON DELETE SET NULL, nullable |
| rawg_id | Integer | RAWG game ID, nullable |
| cover_url | String(500) | RAWG CDN image URL, nullable |
| release_year | Integer | nullable |
| genres | String(200) | Comma-separated, nullable |
| platforms | String(300) | Comma-separated, nullable |
| created_at | DateTime | `datetime.utcnow`, NOT NULL |
| updated_at | DateTime | `datetime.utcnow` + onupdate, NOT NULL |

`Game.to_dict()` serialises all fields to a plain dict for JSON responses.

---

## Routes

| Blueprint | Method | Path | Purpose |
|---|---|---|---|
| main | GET | `/` | Dashboard — counts + top backlog |
| main | GET | `/api/games/search?q=` | RAWG proxy → JSON for forms |
| playing | GET | `/playing/` | Active library (Playing + On Hold) |
| playing | GET | `/playing/<id>` | Game detail + status change |
| playing | GET/POST | `/playing/add` | Add game |
| playing | GET/POST | `/playing/<id>/edit` | Edit game |
| playing | POST | `/playing/<id>/status` | Quick status change |
| playing | POST | `/playing/<id>/delete` | Delete game |
| backlog | GET | `/backlog/` | Backlog grouped by category |
| backlog | GET/POST | `/backlog/add` | Add to backlog |
| backlog | POST | `/backlog/reorder` | SortableJS drag-and-drop (JSON) |
| backlog | POST | `/backlog/<id>/promote` | Move to active library |
| backlog | POST | `/backlog/<id>/delete` | Delete game |
| backlog | GET/POST | `/backlog/categories` | Manage categories |
| backlog | POST | `/backlog/categories/<id>/delete` | Delete category |

---

## Key Behaviours to Preserve

- **Drag-and-drop reorder** saves immediately via `fetch()` POST to `/backlog/reorder` with a JSON array of ordered game IDs. The route updates each game's `rank` in a loop and commits.
- **Promote to active** sets `section='active'`, `status='Playing'`, `rank=0`, `category_id=None`. Redirects to `/playing/`.
- **Active list** shows only `Playing` and `On Hold`. `Dropped` and `Completed` are accessible via the detail page.
- **Backlog list** groups by category (alphabetical), games within each group ordered by `rank ASC` via the relationship's `order_by`.
- **RAWG fields are always nullable** — every form works without an API key. Cover art is a CDN URL loaded directly by the browser; nothing is stored locally.
- The app **binds to TAILSCALE_IP** from `.env` — never `0.0.0.0`.
- Always **create a branch and open a PR** when a task is complete.

---

## Known Gotchas

- **`db.create_all()` creates no tables** if models haven't been imported first. SQLAlchemy only registers a model when its module is imported. Always import `models` before calling `create_all()`:
  ```python
  from app import db, models
  db.create_all()
  ```
  The app factory already does `from app import models` so this is handled at runtime — the issue only surfaces in a raw Python shell without the factory.

- **MySQL lock wait timeout** in `flask shell` if a previous shell session left an open transaction. Exit all shells, wait a moment, retry.

- **`flask run` ignores `run.py`** and binds to `127.0.0.1` regardless of `TAILSCALE_IP`. Use `python run.py` to get Tailscale binding.

- **`flask seed` wipes all game and category data** before re-inserting. Do not run it against production data you want to keep.

---

## RAWG Integration

`app/utils/rawg.py` exposes three functions:

```python
search_games(query, page_size=10)  # → list of RAWG result dicts
get_game(rawg_id)                  # → single RAWG game dict
extract_metadata(rawg_game)        # → dict of fields we persist
```

`extract_metadata` returns: `rawg_id`, `cover_url`, `release_year`, `genres`, `platforms`.

The `/api/games/search?q=` endpoint proxies RAWG and returns JSON consumed by the add/edit form search dropdowns. Returns `[]` silently if `RAWG_API_KEY` is not set.

---

## Running in Production

```bash
gunicorn -w 2 -b <tailscale-ip>:<port> "app:create_app()"
```

Managed via `systemd` for auto-restart. `.env` on the server holds all secrets.

---

## What Not to Do

- Do not expose the app on `0.0.0.0` — Tailscale IP binding only
- Do not commit `.env`
- Do not add user accounts or a login system — Tailscale handles access
- Do not use `flask run` in production — use Gunicorn
- Do not run `flask seed` against a database with real data you want to keep
