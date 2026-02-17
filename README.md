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
- Drag-and-drop to reorder games within each category
- One-click promote to active library

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
| Network / Auth | Tailscale |

---

## Project Structure

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
│   │   ├── base.html        # Base template with nav and CDN links
│   │   ├── main/
│   │   ├── playing/
│   │   └── backlog/
│   └── static/
├── config.py                # Flask config classes, loads from .env
├── run.py                   # Entry point for local dev
├── requirements.txt
└── .env                     # Secrets — never commit
```

---

## Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Create a `.env` file**
```
FLASK_SECRET_KEY=your-secret-key-here
DATABASE_URL=mysql+pymysql://user:password@host/dbname
FLASK_ENV=development
```

**3. Initialize the database**
```bash
flask shell
>>> from app import db
>>> db.create_all()
```

**4. Run locally**
```bash
python run.py
# or
flask run
```

---

## Production

Runs under Gunicorn, bound to the server's Tailscale IP only (never `0.0.0.0`):

```bash
gunicorn -w 2 -b <tailscale-ip>:<port> "app:create_app()"
```

Managed via a `systemd` service for auto-restart on reboot. Secrets are loaded from `.env` at startup via `python-dotenv`.
