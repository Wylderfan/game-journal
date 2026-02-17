from flask import Blueprint, render_template

playing_bp = Blueprint("playing", __name__)


@playing_bp.route("/")
def index():
    return render_template("playing/index.html")
