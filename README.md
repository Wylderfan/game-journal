# game-journal

A personal, private game library journal built with Flask. Track games you're actively playing with timestamped check-ins, manage your backlog by category, and get a ranked play-next list driven by a per-game survey and your current mood preferences.

Access is restricted entirely by Tailscale — no login system. If you're on the Tailnet, you can access the app.

---

## Features

**Multiple Profiles**
- Switch between named profiles from the nav bar (e.g. Player 1, Player 2)
- Every game, category, check-in, and mood preference is scoped per profile
- Profiles are defined in `.env` — no admin UI needed

**Active Library**
- Log games you're currently playing or have on hold
- Track status: Playing, On Hold, Dropped, Completed
- View archived (Dropped/Completed) games in the same page
- Log timestamped check-ins with hours played, a note, and optional status change
- Fill out a finish survey when you complete a game (overall rating, difficulty, would-play-again, hours to finish)

**Backlog Manager**
- Organize unplayed games into user-defined categories (many-to-many)
- Games can belong to multiple categories
- Drag categories to reorder their priority — higher-ranked categories get a scoring bonus
- Rename and delete categories in place
- One-click promote to active library

**Play Next**
- Cross-category ranked list of what to play next
- Includes both backlog games and currently active (Playing/On Hold) games
- Score is computed from a per-game survey filled in at add/edit time:
  - Hype (1–5 stars)
  - Estimated length — Short/Medium/Long/Very Long
  - Series continuity bonus
  - Mood blend — five sliders (Chill / Intense / Story / Action / Exploration)
- Category priority rank adds a bonus to every game in higher-priority categories
- Per-profile mood preferences (set on the Categories page) are matched against each game's mood blend via a dot product
- Playing games get a +30 bonus; On Hold games get a –15 penalty
- All scoring weights are in `app/scoring.py` — edit to tune without touching routes

**Dashboard**
- At-a-glance stats: playing count, on hold, backlog size, completed count
- Up Next widget showing the top 5 scored games

---

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3 |
| Web Framework | Flask |
| ORM | Flask-SQLAlchemy |
| Database | MySQL via PyMySQL |
| Templates | Jinja2 |
| Styling | Tailwind CSS (CDN) |
| Drag-and-Drop | SortableJS (CDN) |
| Production Server | Gunicorn |
| Environment Vars | python-dotenv |
| Network / Auth | Tailscale |
| Game Metadata API | RAWG (rawg.io) |

---

## Project Structure

```
game-journal/
├── app/
│   ├── __init__.py          # App factory, db init, blueprint + CLI registration
│   ├── models.py            # SQLAlchemy models: Game, ProfileGame, Category, MoodPreferences, CheckIn
│   ├── scoring.py           # Play-next scoring weights — edit to tune the algorithm
│   ├── seeds.py             # flask seed CLI command
│   ├── backup.py            # flask db-backup / db-restore CLI commands
│   ├── blueprints/
│   │   ├── main.py          # Dashboard (/), profile switcher, RAWG search proxy
│   │   ├── playing.py       # Active library routes (/playing)
│   │   └── backlog.py       # Backlog routes (/backlog)
│   ├── utils/
│   │   ├── helpers.py       # current_profile(), _int(), _float()
│   │   └── rawg.py          # RAWG API helpers
│   ├── templates/
│   │   ├── base.html        # Base template with nav and CDN links
│   │   ├── macros.html      # Shared Jinja2 macros (star ratings, etc.)
│   │   ├── errors/
│   │   │   ├── 404.html
│   │   │   └── 500.html
│   │   ├── main/
│   │   │   └── index.html   # Dashboard — stat cards + top 5 play next
│   │   ├── playing/
│   │   │   ├── index.html   # Active library — Playing, On Hold, Archived
│   │   │   ├── detail.html  # Per-game detail with check-in form
│   │   │   ├── form.html    # Edit form (survey + RAWG search)
│   │   │   └── finish_survey.html
│   │   └── backlog/
│   │       ├── index.html   # Sortable category groups
│   │       ├── add.html     # Add to backlog (RAWG search + survey + categories)
│   │       ├── edit.html    # Edit backlog game (full survey editing)
│   │       ├── play_next.html
│   │       └── categories.html  # Manage categories + mood preferences
│   └── static/
├── backups/                 # Created by flask db-backup
├── deploy/
│   ├── game-journal.service # systemd unit template
│   └── game-journal.openrc  # OpenRC init script template (Gentoo)
├── config.py                # DevelopmentConfig / ProductionConfig, loads PROFILES
├── run.py                   # Entry point for local dev
├── requirements.txt
└── .env                     # Secrets — never commit
```

---

## RAWG API

RAWG provides game metadata — cover art, release year, genres, and platforms. It is **optional**; every form works without it, you just won't get search suggestions or cover images.

**Getting a key**
1. Create a free account at [rawg.io](https://rawg.io)
2. Go to [rawg.io/apidocs](https://rawg.io/apidocs) and generate an API key
3. Add it to your `.env` as `RAWG_API_KEY`

The free tier allows 20,000 requests/month, which is well beyond what a personal journal will ever use.

**What it's used for**
- The add/edit forms include a search box that queries RAWG as you type (`/api/games/search?q=`). Selecting a result pre-fills the game name and stores the cover URL, release year, genres, and platforms.
- `flask seed` fetches cover art from RAWG for the example games if the key is set.
- Cover images are CDN URLs loaded directly by the browser — nothing is stored locally.

**Without a key**
If `RAWG_API_KEY` is not set, the search endpoint returns `[]` silently and the search box simply does nothing. You can still add games manually by typing the name directly.

---

## Setup

**1. Install dependencies**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Create a `.env` file**
```
FLASK_SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://user:password@host/dbname
FLASK_ENV=development
RAWG_API_KEY=your-rawg-api-key        # from rawg.io/apidocs — free account
TAILSCALE_IP=100.x.x.x                # from: tailscale ip -4
PORT=5000
PROFILES=Player 1,Player 2            # comma-separated; first is the default
```

**3. Initialize the database**
```bash
flask shell
>>> from app import db, models
>>> db.create_all()
```

**4. (Optional) Seed with example data**
```bash
flask seed
```

> **Warning:** `flask seed` wipes all game and category data before re-inserting. Do not run it against a database with real data you want to keep.

**5. Run locally**
```bash
python run.py
```

---

## Database Backup & Restore

The app includes CLI commands that wrap `mysqldump` and `mysql`:

```bash
# Dump to backups/<dbname>_<timestamp>.sql
flask db-backup

# Dump to a specific directory
flask db-backup --output-dir /path/to/backups

# Restore from a file (prompts for confirmation)
flask db-restore backups/mydb_20260222_120000.sql

# Restore without confirmation prompt
flask db-restore backups/mydb_20260222_120000.sql --yes
```

Both commands read connection info from `DATABASE_URL` in `.env`.

---

## Production

Runs under Gunicorn via `systemd` — do not run Gunicorn directly. The service unit at `deploy/game-journal.service` is a template; fill in the placeholders and install it on the server:

**1. Fill in `deploy/game-journal.service`**
Replace `<your-linux-user>`, `/path/to/game-journal`, and `<tailscale-ip>:<port>` with real values.

**2. Install and enable the service**
```bash
sudo cp deploy/game-journal.service /etc/systemd/system/game-journal.service
sudo systemctl daemon-reload
sudo systemctl enable game-journal
sudo systemctl start game-journal
```

**Useful commands**
```bash
sudo systemctl status game-journal   # check running state
journalctl -u game-journal           # view logs
```

systemd handles starting Gunicorn on boot and restarting it on failure. Secrets are loaded from `.env` at startup via `python-dotenv`.

---

### OpenRC (Gentoo)

A template init script is provided at `deploy/game-journal.openrc`.

**1. Fill in `deploy/game-journal.openrc`**
Replace `<your-linux-user>`, `/path/to/game-journal`, and `<tailscale-ip>:<port>` with real values.

**2. Install and enable the service**
```bash
sudo cp deploy/game-journal.openrc /etc/init.d/game-journal
sudo chmod +x /etc/init.d/game-journal
sudo rc-update add game-journal default
sudo rc-service game-journal start
```

**Useful commands**
```bash
sudo rc-service game-journal status   # check running state
sudo rc-service game-journal restart  # restart after config changes
```

The init script sources `.env` via `start_pre` before Gunicorn starts, so all environment variables are available at runtime.
