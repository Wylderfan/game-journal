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

---

## Project Status

Early-stage — stack and architecture are confirmed. No application code exists yet. Only this file and a README are present.

**Build phases remaining (in order):**
1. Project scaffolding and virtual environment
2. Database schema design and SQLAlchemy models
3. MySQL connection and table generation
4. Flask Blueprints and CRUD route structure
5. Active Library views and forms
6. Backlog views, category management, and drag-and-drop ranking
7. Dashboard and base template
8. Error handling and responsive layout polish
9. Gunicorn + systemd deployment on Tailscale-bound IP

---

## Project Structure (target layout)

```
game-journal/
├── app/
│   ├── __init__.py          # App factory, db init, blueprint registration
│   ├── models.py            # SQLAlchemy models: Game, Category
│   ├── blueprints/
│   │   ├── main.py          # Dashboard route (/)
│   │   ├── playing.py       # Active library routes (/playing)
│   │   └── backlog.py       # Backlog routes (/backlog)
│   ├── templates/
│   │   ├── base.html        # Base Jinja2 template with nav, CDN links
│   │   ├── main/
│   │   ├── playing/
│   │   └── backlog/
│   └── static/              # Any local static assets if needed
├── .env                     # Secret key, DB connection string (never commit)
├── .gitignore
├── requirements.txt
├── config.py                # Flask config classes, loads from .env
└── run.py                   # Entry point for local dev
```

---

## Setup

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Expected `requirements.txt` contents:**
```
flask
flask-sqlalchemy
pymysql
gunicorn
python-dotenv
```

**Environment variables (`.env` file):**
```
FLASK_SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://user:password@host/dbname
FLASK_ENV=development
```

**Initialize the database (once models exist):**
```bash
flask shell
>>> from app import db
>>> db.create_all()
```

**Run locally:**
```bash
flask run
# or
python run.py
```

---

## Database Models

### `Category`
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | User-defined label |

### `Game`
| Field | Type | Notes |
|---|---|---|
| id | Integer | Primary key |
| name | String | Required |
| section | Enum | `'active'` or `'backlog'` |
| status | Enum | `'Playing'`, `'On Hold'`, `'Dropped'`, `'Completed'` |
| enjoyment | Integer | 1–5 scale, nullable |
| motivation | Integer | 1–5 scale, nullable |
| notes | Text | Freeform, nullable |
| rank | Integer | Backlog priority order within category, default 0 |
| category_id | ForeignKey | References `Category.id`, nullable |
| created_at | DateTime | Defaults to `datetime.utcnow` |
| updated_at | DateTime | Updates on modification |

**Relationship:** `Category` has many `Game`s. Access via `category.games`.

---

## Flask Blueprints

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `main` | `/` | Dashboard summary counts and top backlog picks |
| `playing` | `/playing` | Active library list, add, edit, status changes, archive |
| `backlog` | `/backlog` | Backlog list, categories, add game, reorder, promote |

---

## Key Behaviours to Preserve

- **Drag-and-drop reorder** saves to the database immediately via a `fetch()` POST to `/backlog/reorder` with a JSON array of ordered game IDs. The Flask route updates each game's `rank` field in a loop and commits.
- **Promote to active** updates `section` to `'active'`, sets `status` to `'Playing'`, and nulls out `rank`. It redirects to `/playing`.
- **Active list** only shows `Playing` and `On Hold` by default. `Dropped` and `Completed` are accessible via a separate toggle or tab.
- **Backlog list** groups games by category, ordering categories alphabetically and games within each category by `rank ASC`.
- The app **binds to the Tailscale IP only** — never `0.0.0.0`.

---

## Running in Production

```bash
gunicorn -w 2 -b <tailscale-ip>:<port> "app:create_app()"
```

Managed via `systemd` service for auto-restart on reboot. The `.env` file on the server holds all secrets and is loaded at startup via `python-dotenv`.

---

## Testing

When a test suite is added (pytest), run with:
```bash
pytest
# single test:
pytest tests/test_file.py::test_name
```

---

## What Not to Do

- Do not expose the app on `0.0.0.0` or any public interface — Tailscale IP binding only
- Do not commit `.env` to version control
- Do not add user accounts, registration, or a login system — Tailscale handles access entirely
- Do not use Flask's built-in development server in production — use Gunicorn
