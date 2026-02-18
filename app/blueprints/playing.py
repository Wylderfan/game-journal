from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import Game

playing_bp = Blueprint("playing", __name__)

STATUSES = ["Playing", "On Hold", "Dropped", "Completed"]


def _int(value):
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


@playing_bp.route("/")
def index():
    playing = (
        Game.query.filter_by(section="active", status="Playing")
        .order_by(Game.name).all()
    )
    on_hold = (
        Game.query.filter_by(section="active", status="On Hold")
        .order_by(Game.name).all()
    )
    archived = (
        Game.query.filter(
            Game.section == "active",
            Game.status.in_(["Dropped", "Completed"]),
        )
        .order_by(Game.status, Game.name).all()
    )
    return render_template("playing/index.html", playing=playing, on_hold=on_hold, archived=archived)


@playing_bp.route("/<int:game_id>")
def detail(game_id):
    game = db.get_or_404(Game, game_id)
    return render_template("playing/detail.html", game=game, statuses=STATUSES)


@playing_bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("playing.add"))

        game = Game(
            name=name,
            section="active",
            status=request.form.get("status", "Playing"),
            enjoyment=_int(request.form.get("enjoyment")),
            motivation=_int(request.form.get("motivation")),
            notes=request.form.get("notes", "").strip() or None,
            rawg_id=_int(request.form.get("rawg_id")),
            cover_url=request.form.get("cover_url") or None,
            release_year=_int(request.form.get("release_year")),
            genres=request.form.get("genres") or None,
            platforms=request.form.get("platforms") or None,
        )
        db.session.add(game)
        db.session.commit()
        flash(f"'{game.name}' added to active library.", "success")
        return redirect(url_for("playing.index"))

    return render_template("playing/form.html", game=None, statuses=STATUSES)


@playing_bp.route("/<int:game_id>/edit", methods=["GET", "POST"])
def edit(game_id):
    game = db.get_or_404(Game, game_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("playing.edit", game_id=game_id))

        game.name       = name
        game.status     = request.form.get("status", game.status)
        game.enjoyment  = _int(request.form.get("enjoyment"))
        game.motivation = _int(request.form.get("motivation"))
        game.notes      = request.form.get("notes", "").strip() or None
        # Only overwrite RAWG fields if the form sent something new
        game.cover_url    = request.form.get("cover_url")    or game.cover_url
        game.rawg_id      = _int(request.form.get("rawg_id")) or game.rawg_id
        game.release_year = _int(request.form.get("release_year")) or game.release_year
        game.genres       = request.form.get("genres")    or game.genres
        game.platforms    = request.form.get("platforms") or game.platforms

        db.session.commit()
        flash(f"'{game.name}' updated.", "success")
        return redirect(url_for("playing.index"))

    return render_template("playing/form.html", game=game, statuses=STATUSES)


@playing_bp.route("/<int:game_id>/status", methods=["POST"])
def set_status(game_id):
    game = db.get_or_404(Game, game_id)
    new_status = request.form.get("status")
    if new_status in STATUSES:
        game.status = new_status
        db.session.commit()
    return redirect(url_for("playing.detail", game_id=game_id))


@playing_bp.route("/<int:game_id>/delete", methods=["POST"])
def delete(game_id):
    game = db.get_or_404(Game, game_id)
    name = game.name
    db.session.delete(game)
    db.session.commit()
    flash(f"'{name}' removed.", "success")
    return redirect(url_for("playing.index"))
