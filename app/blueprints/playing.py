from flask import Blueprint, render_template
from app.models import Game

playing_bp = Blueprint("playing", __name__)


@playing_bp.route("/")
def index():
    playing = Game.query.filter_by(section="active", status="Playing").order_by(Game.name).all()
    on_hold = Game.query.filter_by(section="active", status="On Hold").order_by(Game.name).all()
    return render_template("playing/index.html", playing=playing, on_hold=on_hold)
