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


@click.command("seed")
@with_appcontext
def seed_command():
    """Wipe and re-seed the database with the default category list for all profiles."""
    profiles_env = os.environ.get("PROFILES", "Player 1")
    profiles = [p.strip() for p in profiles_env.split(",") if p.strip()]

    click.echo("Clearing existing data...")
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=0"))
    db.session.execute(db.text("DELETE FROM checkins"))
    db.session.execute(db.text("DELETE FROM profile_game_categories"))
    db.session.execute(db.text("DELETE FROM profile_games"))
    Game.query.delete()
    Category.query.delete()
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS=1"))
    db.session.commit()

    click.echo(f"Creating categories for {len(profiles)} profile(s): {profiles}...")
    for profile in profiles:
        for rank, name in enumerate(CATEGORIES, start=1):
            db.session.add(Category(name=name, rank=rank, profile_id=profile))
    db.session.commit()

    click.echo(f"Done. {len(CATEGORIES)} categories seeded per profile.")
