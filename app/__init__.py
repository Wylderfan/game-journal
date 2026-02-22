import os
import click
from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
from config import config

db = SQLAlchemy()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    from app import models  # noqa: F401 — registers models with SQLAlchemy metadata

    from app.blueprints.main import main_bp
    from app.blueprints.playing import playing_bp
    from app.blueprints.backlog import backlog_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(playing_bp, url_prefix="/playing")
    app.register_blueprint(backlog_bp, url_prefix="/backlog")

    from app.seeds import seed_command
    app.cli.add_command(seed_command)

    from app.backup import backup_command, restore_command
    app.cli.add_command(backup_command)
    app.cli.add_command(restore_command)

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables if they don't already exist."""
        db.create_all()
        click.echo("Database tables ready.")

    @app.context_processor
    def inject_profile():
        profiles = app.config["PROFILES"]
        current = session.get("profile")
        if current not in profiles:
            current = profiles[0]
        return {"current_profile": current, "profiles": profiles}

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
