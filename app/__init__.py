from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config

db = SQLAlchemy()


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)

    from app.blueprints.main import main_bp
    from app.blueprints.playing import playing_bp
    from app.blueprints.backlog import backlog_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(playing_bp, url_prefix="/playing")
    app.register_blueprint(backlog_bp, url_prefix="/backlog")

    return app
