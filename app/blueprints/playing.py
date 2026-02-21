from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import Game, CheckIn, STATUSES
from app.utils.helpers import _int, _float

playing_bp = Blueprint("playing", __name__)


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

        try:
            db.session.commit()
            flash(f"'{game.name}' updated.", "success")
            return redirect(url_for("playing.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("playing.edit", game_id=game_id))

    return render_template("playing/form.html", game=game, statuses=STATUSES)


@playing_bp.route("/<int:game_id>/status", methods=["POST"])
def set_status(game_id):
    game = db.get_or_404(Game, game_id)
    new_status = request.form.get("status")
    if new_status in STATUSES:
        game.status = new_status
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Status update failed.", "error")
    return redirect(url_for("playing.detail", game_id=game_id))


@playing_bp.route("/<int:game_id>/checkin", methods=["POST"])
def checkin(game_id):
    game = db.get_or_404(Game, game_id)

    new_status   = request.form.get("status") or None
    new_enjoyment  = _int(request.form.get("enjoyment"))
    new_motivation = _int(request.form.get("motivation"))

    checkin_obj = CheckIn(
        game_id=game_id,
        motivation=new_motivation,
        enjoyment=new_enjoyment,
        note=request.form.get("note", "").strip() or None,
        hours_played=_float(request.form.get("hours_played")),
        status=new_status if new_status in STATUSES else None,
    )

    if new_status in STATUSES:
        game.status = new_status
    if new_enjoyment is not None:
        game.enjoyment = new_enjoyment
    if new_motivation is not None:
        game.motivation = new_motivation
    if request.form.get("finished"):
        game.finished         = True
        game.overall_rating   = _int(request.form.get("overall_rating"))
        game.would_play_again = request.form.get("would_play_again") or None
        game.hours_to_finish  = _int(request.form.get("hours_to_finish"))
        game.difficulty       = _int(request.form.get("difficulty"))

    db.session.add(checkin_obj)
    try:
        db.session.commit()
        flash(f"Check-in saved for '{game.name}'.", "success")
    except Exception:
        db.session.rollback()
        flash("Check-in could not be saved. Please try again.", "error")

    return redirect(url_for("playing.index"))


@playing_bp.route("/<int:game_id>/finish", methods=["GET", "POST"])
def finish(game_id):
    game = db.get_or_404(Game, game_id)

    if request.method == "POST":
        game.finished         = True
        game.overall_rating   = _int(request.form.get("overall_rating"))
        game.would_play_again = request.form.get("would_play_again") or None
        game.hours_to_finish  = _int(request.form.get("hours_to_finish"))
        game.difficulty       = _int(request.form.get("difficulty"))
        try:
            db.session.commit()
            flash(f"'{game.name}' marked as finished.", "success")
        except Exception:
            db.session.rollback()
            flash("Could not save survey. Please try again.", "error")
        return redirect(url_for("playing.detail", game_id=game_id))

    return render_template("playing/finish_survey.html", game=game)


@playing_bp.route("/<int:game_id>/delete", methods=["POST"])
def delete(game_id):
    game = db.get_or_404(Game, game_id)
    name = game.name
    db.session.delete(game)
    try:
        db.session.commit()
        flash(f"'{name}' removed.", "success")
        return redirect(url_for("playing.index"))
    except Exception:
        db.session.rollback()
        flash("Could not remove the game. Please try again.", "error")
        return redirect(url_for("playing.detail", game_id=game_id))
