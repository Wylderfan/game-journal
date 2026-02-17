from flask import Blueprint, render_template

backlog_bp = Blueprint("backlog", __name__)


@backlog_bp.route("/")
def index():
    return render_template("backlog/index.html")
