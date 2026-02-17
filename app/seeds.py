import click
from flask import current_app
from flask.cli import with_appcontext
from app import db
from app.models import Category, Game


CATEGORIES = [
    "Action RPG",
    "Platformer",
    "Strategy",
    "Indie",
]

ACTIVE_GAMES = [
    {
        "name": "Elden Ring",
        "section": "active",
        "status": "Playing",
        "enjoyment": 5,
        "motivation": 5,
        "notes": "Incredible open world. Currently exploring Liurnia.",
        "genres": "Action, RPG",
        "platforms": "PC, PS5, Xbox Series X",
        "release_year": 2022,
    },
    {
        "name": "Hades",
        "section": "active",
        "status": "On Hold",
        "enjoyment": 4,
        "motivation": 3,
        "notes": "Great game, just taking a break after a dozen runs.",
        "genres": "Action, Roguelike, Indie",
        "platforms": "PC, Switch, PS4",
        "release_year": 2020,
    },
    {
        "name": "Disco Elysium",
        "section": "active",
        "status": "Playing",
        "enjoyment": 5,
        "motivation": 4,
        "notes": "Absolutely wild writing. Playing the detective badly on purpose.",
        "genres": "RPG",
        "platforms": "PC, PS4, PS5",
        "release_year": 2019,
    },
]

# Each entry: (game data, category name, rank within that category)
BACKLOG_GAMES = [
    (
        {
            "name": "Hollow Knight",
            "section": "backlog",
            "status": None,
            "genres": "Action, Adventure, Indie",
            "platforms": "PC, Switch, PS4",
            "release_year": 2017,
        },
        "Indie",
        1,
    ),
    (
        {
            "name": "Celeste",
            "section": "backlog",
            "status": None,
            "genres": "Platformer, Indie",
            "platforms": "PC, Switch, PS4",
            "release_year": 2018,
        },
        "Platformer",
        1,
    ),
    (
        {
            "name": "Ori and the Blind Forest",
            "section": "backlog",
            "status": None,
            "genres": "Platformer, Adventure",
            "platforms": "PC, Switch, Xbox One",
            "release_year": 2015,
        },
        "Platformer",
        2,
    ),
    (
        {
            "name": "Into the Breach",
            "section": "backlog",
            "status": None,
            "genres": "Strategy, Indie",
            "platforms": "PC, Switch",
            "release_year": 2018,
        },
        "Strategy",
        1,
    ),
    (
        {
            "name": "Divinity: Original Sin 2",
            "section": "backlog",
            "status": None,
            "genres": "RPG, Strategy",
            "platforms": "PC, PS4, Xbox One, Switch",
            "release_year": 2017,
        },
        "Action RPG",
        1,
    ),
    (
        {
            "name": "Baldur's Gate 3",
            "section": "backlog",
            "status": None,
            "genres": "RPG, Strategy",
            "platforms": "PC, PS5",
            "release_year": 2023,
        },
        "Action RPG",
        2,
    ),
]


@click.command("seed")
@with_appcontext
def seed_command():
    """Wipe and re-seed the database with example data."""
    click.echo("Clearing existing data...")
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=0"))
    Game.query.delete()
    Category.query.delete()
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=1"))
    db.session.commit()

    click.echo("Creating categories...")
    cats = {}
    for name in CATEGORIES:
        c = Category(name=name)
        db.session.add(c)
        cats[name] = c
    db.session.flush()  # get IDs without committing

    click.echo("Creating active games...")
    for data in ACTIVE_GAMES:
        db.session.add(Game(**data))

    click.echo("Creating backlog games...")
    for data, cat_name, rank in BACKLOG_GAMES:
        db.session.add(Game(**data, rank=rank, category_id=cats[cat_name].id))

    db.session.commit()
    click.echo(f"Done. {len(ACTIVE_GAMES)} active, {len(BACKLOG_GAMES)} backlog games seeded.")
