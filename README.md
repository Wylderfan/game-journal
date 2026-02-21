# game-journal

A personal, private game library journal built with Flask. Track games you're actively playing with enjoyment and motivation ratings, and manage your backlog with category organization and drag-and-drop prioritization.

Access is restricted entirely by Tailscale — no login system. If you're on the Tailnet, you can access the app.

---

## Features

**Active Library**
- Log games you're currently playing or have on hold
- Rate enjoyment and motivation to finish (1–5 scale)
- Track status: Playing, On Hold, Dropped, Completed
- Add freeform notes per game
- View archived (Dropped/Completed) games separately

**Backlog Manager**
- Organize unplayed games into user-defined categories
- Rename categories in place
- Drag-and-drop to reorder games within each category
- One-click promote to active library

**Dashboard**
- At-a-glance stats: active game count, backlog size, completed count
- Top game per backlog category

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
│   ├── __init__.py          # App factory, db init, blueprint registration
│   ├── models.py            # SQLAlchemy models: Game, Category
│   ├── seeds.py             # flask seed CLI command
│   ├── blueprints/
│   │   ├── main.py          # Dashboard (/) and RAWG search proxy
│   │   ├── playing.py       # Active library routes (/playing)
│   │   └── backlog.py       # Backlog routes (/backlog)
│   ├── utils/
│   │   └── rawg.py          # RAWG API helpers
│   ├── templates/
│   │   ├── base.html        # Base template with nav and CDN links
│   │   ├── main/
│   │   ├── playing/
│   │   └── backlog/
│   └── static/
├── deploy/
│   └── game-journal.service # systemd unit template
├── config.py                # DevelopmentConfig / ProductionConfig, loads from .env
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

**5. Run locally**
```bash
python run.py
```

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
