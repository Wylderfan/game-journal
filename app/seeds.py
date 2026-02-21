import os
import click
from flask.cli import with_appcontext
from app import db
from app.models import Category, Game


# RAWG genre categories in default rank order (user can reorder via the UI)
CATEGORIES = [
    "Action",
    "Indie",
    "Adventure",
    "RPG",
    "Strategy",
    "Shooter",
    "Casual",
    "Simulation",
    "Puzzle",
    "Arcade",
    "Platformer",
    "Massively Multiplayer",
    "Racing",
    "Sports",
    "Fighting",
    "Family",
    "Board Games",
    "Card",
    "Educational",
]

# (game data, category name)
# Survey fields: hype (1-5), estimated_length, series_continuity,
#                mood_chill/intense/story/action/exploration (0-5 each)
BACKLOG_GAMES = [
    (
        {
            "name": "Baldur's Gate 3",
            "section": "backlog",
            "status": None,
            "genres": "RPG, Strategy",
            "platforms": "PC, PS5",
            "release_year": 2023,
            "hype": 5,
            "estimated_length": "Very Long",
            "series_continuity": False,
            "mood_chill": 1,
            "mood_intense": 3,
            "mood_story": 5,
            "mood_action": 3,
            "mood_exploration": 4,
        },
        "RPG",
    ),
    (
        {
            "name": "Hollow Knight",
            "section": "backlog",
            "status": None,
            "genres": "Action, Adventure, Indie",
            "platforms": "PC, Switch, PS4",
            "release_year": 2017,
            "hype": 4,
            "estimated_length": "Medium",
            "series_continuity": False,
            "mood_chill": 3,
            "mood_intense": 3,
            "mood_story": 3,
            "mood_action": 3,
            "mood_exploration": 5,
        },
        "Indie",
    ),
    (
        {
            "name": "Celeste",
            "section": "backlog",
            "status": None,
            "genres": "Platformer, Indie",
            "platforms": "PC, Switch, PS4",
            "release_year": 2018,
            "hype": 5,
            "estimated_length": "Short",
            "series_continuity": False,
            "mood_chill": 1,
            "mood_intense": 5,
            "mood_story": 3,
            "mood_action": 3,
            "mood_exploration": 2,
        },
        "Platformer",
    ),
    (
        {
            "name": "Ori and the Blind Forest",
            "section": "backlog",
            "status": None,
            "genres": "Platformer, Adventure",
            "platforms": "PC, Switch, Xbox One",
            "release_year": 2015,
            "hype": 3,
            "estimated_length": "Short",
            "series_continuity": False,
            "mood_chill": 3,
            "mood_intense": 2,
            "mood_story": 4,
            "mood_action": 2,
            "mood_exploration": 3,
        },
        "Platformer",
    ),
    (
        {
            "name": "Into the Breach",
            "section": "backlog",
            "status": None,
            "genres": "Strategy, Indie",
            "platforms": "PC, Switch",
            "release_year": 2018,
            "hype": 3,
            "estimated_length": "Medium",
            "series_continuity": False,
            "mood_chill": 0,
            "mood_intense": 3,
            "mood_story": 1,
            "mood_action": 2,
            "mood_exploration": 1,
        },
        "Strategy",
    ),
]


def _rawg_meta(name):
    """Fetch RAWG metadata for a game by name. Returns {} silently on failure."""
    if not os.environ.get("RAWG_API_KEY"):
        return {}
    try:
        from app.utils.rawg import search_games, extract_metadata
        results = search_games(name, page_size=1)
        if results:
            return extract_metadata(results[0])
    except Exception as e:
        click.echo(f"  RAWG lookup failed for '{name}': {e}", err=True)
    return {}


@click.command("seed")
@with_appcontext
def seed_command():
    """Wipe and re-seed the database with example data."""
    use_rawg = bool(os.environ.get("RAWG_API_KEY"))
    if use_rawg:
        click.echo("RAWG key found — cover art will be fetched.")
    else:
        click.echo("No RAWG key — seeding without cover art.")

    click.echo("Clearing existing data...")
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=0"))
    db.session.execute(db.text("DELETE FROM game_categories"))
    Game.query.delete()
    Category.query.delete()
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=1"))
    db.session.commit()

    click.echo("Creating categories...")
    cats = {}
    for rank, name in enumerate(CATEGORIES, start=1):
        c = Category(name=name, rank=rank)
        db.session.add(c)
        cats[name] = c
    db.session.flush()

    click.echo("Creating backlog games...")
    for data, cat_name in BACKLOG_GAMES:
        click.echo(f"  {data['name']}...")
        meta = _rawg_meta(data["name"])
        game = Game(**{**data, **meta, "rank": 0})
        db.session.add(game)
        game.categories = [cats[cat_name]]

    db.session.commit()
    click.echo(f"Done. {len(BACKLOG_GAMES)} backlog games seeded.")
