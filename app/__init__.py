import os
from flask import Flask, render_template
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

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app
