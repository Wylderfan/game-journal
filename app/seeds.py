import os
import click
from flask.cli import with_appcontext
from app import db
from app.models import Category, Game, ProfileGame


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

# (game RAWG data, profile-specific data)
BACKLOG_GAMES = [
    (
        {
            "name": "Baldur's Gate 3",
            "genres": "RPG, Strategy",
            "platforms": "PC, PS5",
            "release_year": 2023,
        },
        {
            "section": "backlog",
            "status": None,
            "hype": 5,
            "estimated_length": "Very Long",
            "series_continuity": False,
            "mood_chill": 1,
            "mood_intense": 3,
            "mood_story": 5,
            "mood_action": 3,
            "mood_exploration": 4,
            "rank": 0,
        },
    ),
    (
        {
            "name": "Hollow Knight",
            "genres": "Action, Adventure, Indie",
            "platforms": "PC, Switch, PS4",
            "release_year": 2017,
        },
        {
            "section": "backlog",
            "status": None,
            "hype": 4,
            "estimated_length": "Medium",
            "series_continuity": False,
            "mood_chill": 3,
            "mood_intense": 3,
            "mood_story": 3,
            "mood_action": 3,
            "mood_exploration": 5,
            "rank": 0,
        },
    ),
    (
        {
            "name": "Celeste",
            "genres": "Platformer, Indie",
            "platforms": "PC, Switch, PS4",
            "release_year": 2018,
        },
        {
            "section": "backlog",
            "status": None,
            "hype": 5,
            "estimated_length": "Short",
            "series_continuity": False,
            "mood_chill": 1,
            "mood_intense": 5,
            "mood_story": 3,
            "mood_action": 3,
            "mood_exploration": 2,
            "rank": 0,
        },
    ),
    (
        {
            "name": "Ori and the Blind Forest",
            "genres": "Platformer, Adventure",
            "platforms": "PC, Switch, Xbox One",
            "release_year": 2015,
        },
        {
            "section": "backlog",
            "status": None,
            "hype": 3,
            "estimated_length": "Short",
            "series_continuity": False,
            "mood_chill": 3,
            "mood_intense": 2,
            "mood_story": 4,
            "mood_action": 2,
            "mood_exploration": 3,
            "rank": 0,
        },
    ),
    (
        {
            "name": "Into the Breach",
            "genres": "Strategy, Indie",
            "platforms": "PC, Switch",
            "release_year": 2018,
        },
        {
            "section": "backlog",
            "status": None,
            "hype": 3,
            "estimated_length": "Medium",
            "series_continuity": False,
            "mood_chill": 0,
            "mood_intense": 3,
            "mood_story": 1,
            "mood_action": 2,
            "mood_exploration": 1,
            "rank": 0,
        },
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
    # Determine first profile name from env
    profiles_env = os.environ.get("PROFILES", "Player 1")
    first_profile = [p.strip() for p in profiles_env.split(",") if p.strip()][0]

    use_rawg = bool(os.environ.get("RAWG_API_KEY"))
    if use_rawg:
        click.echo("RAWG key found — cover art will be fetched.")
    else:
        click.echo("No RAWG key — seeding without cover art.")

    click.echo("Clearing existing data...")
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=0"))
    db.session.execute(db.text("DELETE FROM profile_games"))
    db.session.execute(db.text("DELETE FROM checkins"))
    Game.query.delete()
    Category.query.delete()
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=1"))
    db.session.commit()

    click.echo("Creating categories...")
    for rank, name in enumerate(CATEGORIES, start=1):
        db.session.add(Category(name=name, rank=rank, profile_id=first_profile))
    db.session.commit()

    click.echo(f"Creating backlog games (profile: {first_profile!r})...")
    for game_data, profile_data in BACKLOG_GAMES:
        click.echo(f"  {game_data['name']}...")
        meta = _rawg_meta(game_data["name"])
        game = Game(**{**game_data, **meta})
        db.session.add(game)
        db.session.flush()  # get game.id

        pg = ProfileGame(profile_id=first_profile, game_id=game.id, **profile_data)
        db.session.add(pg)

    db.session.commit()
    click.echo(f"Done. {len(BACKLOG_GAMES)} backlog games seeded.")
