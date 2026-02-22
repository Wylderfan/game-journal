from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import Game, ProfileGame, Category, CheckIn, STATUSES
from app.utils.helpers import _int, _float, current_profile

playing_bp = Blueprint("playing", __name__)


@playing_bp.route("/")
def index():
    profile = current_profile()
    playing = (
        ProfileGame.query
        .filter_by(profile_id=profile, section="active", status="Playing")
        .join(ProfileGame.game).order_by(Game.name)
        .all()
    )
    on_hold = (
        ProfileGame.query
        .filter_by(profile_id=profile, section="active", status="On Hold")
        .join(ProfileGame.game).order_by(Game.name)
        .all()
    )
    archived = (
        ProfileGame.query
        .filter(
            ProfileGame.profile_id == profile,
            ProfileGame.section == "active",
            ProfileGame.status.in_(["Dropped", "Completed"]),
        )
        .join(ProfileGame.game).order_by(ProfileGame.status, Game.name)
        .all()
    )
    return render_template("playing/index.html", playing=playing, on_hold=on_hold, archived=archived)


@playing_bp.route("/<int:pg_id>")
def detail(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()
    checkins = CheckIn.query.filter_by(game_id=pg.game_id).order_by(CheckIn.created_at.desc()).all()
    return render_template("playing/detail.html", game=pg, statuses=STATUSES, checkins=checkins)


@playing_bp.route("/<int:pg_id>/edit", methods=["GET", "POST"])
def edit(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()
    categories = Category.query.filter_by(profile_id=profile).order_by(Category.rank, Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("playing.edit", pg_id=pg_id))

        # Per-profile fields
        pg.status            = request.form.get("status", pg.status)
        pg.hype              = _int(request.form.get("hype"))
        pg.estimated_length  = request.form.get("estimated_length") or None
        pg.series_continuity = bool(request.form.get("series_continuity"))
        pg.mood_chill        = _int(request.form.get("mood_chill"))
        pg.mood_intense      = _int(request.form.get("mood_intense"))
        pg.mood_story        = _int(request.form.get("mood_story"))
        pg.mood_action       = _int(request.form.get("mood_action"))
        pg.mood_exploration  = _int(request.form.get("mood_exploration"))
        pg.notes             = request.form.get("notes", "").strip() or None

        # RAWG/identity fields on the shared Game row
        pg.game.name         = name
        pg.game.cover_url    = request.form.get("cover_url")    or pg.game.cover_url
        pg.game.rawg_id      = _int(request.form.get("rawg_id")) or pg.game.rawg_id
        pg.game.release_year = _int(request.form.get("release_year")) or pg.game.release_year
        pg.game.genres       = request.form.get("genres")       or pg.game.genres
        pg.game.platforms    = request.form.get("platforms")    or pg.game.platforms

        cat_ids = [_int(v) for v in request.form.getlist("category_ids") if v]
        pg.categories = Category.query.filter(Category.id.in_(cat_ids), Category.profile_id == profile).all() if cat_ids else []

        try:
            db.session.commit()
            flash(f"'{pg.name}' updated.", "success")
            return redirect(url_for("playing.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("playing.edit", pg_id=pg_id))

    return render_template("playing/form.html", game=pg, statuses=STATUSES, categories=categories)


@playing_bp.route("/<int:pg_id>/status", methods=["POST"])
def set_status(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()
    new_status = request.form.get("status")
    if new_status in STATUSES:
        pg.status = new_status
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash("Status update failed.", "error")
    return redirect(url_for("playing.detail", pg_id=pg_id))


@playing_bp.route("/<int:pg_id>/checkin", methods=["POST"])
def checkin(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()

    new_status = request.form.get("status") or None
    new_hype   = _int(request.form.get("hype"))

    # CheckIn still uses game_id FK until issue #47 migrates to profile_game_id
    checkin_obj = CheckIn(
        game_id=pg.game_id,
        note=request.form.get("note", "").strip() or None,
        hours_played=_float(request.form.get("hours_played")),
        status=new_status if new_status in STATUSES else None,
    )

    if new_status in STATUSES:
        pg.status = new_status
    if new_hype is not None:
        pg.hype = new_hype
    if request.form.get("finished"):
        pg.finished         = True
        pg.overall_rating   = _int(request.form.get("overall_rating"))
        pg.would_play_again = request.form.get("would_play_again") or None
        pg.hours_to_finish  = _int(request.form.get("hours_to_finish"))
        pg.difficulty       = _int(request.form.get("difficulty"))

    db.session.add(checkin_obj)
    try:
        db.session.commit()
        flash(f"Check-in saved for '{pg.name}'.", "success")
    except Exception:
        db.session.rollback()
        flash("Check-in could not be saved. Please try again.", "error")

    return redirect(url_for("playing.index"))


@playing_bp.route("/<int:pg_id>/finish", methods=["GET", "POST"])
def finish(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()

    if request.method == "POST":
        pg.finished         = True
        pg.overall_rating   = _int(request.form.get("overall_rating"))
        pg.would_play_again = request.form.get("would_play_again") or None
        pg.hours_to_finish  = _int(request.form.get("hours_to_finish"))
        pg.difficulty       = _int(request.form.get("difficulty"))
        try:
            db.session.commit()
            flash(f"'{pg.name}' marked as finished.", "success")
        except Exception:
            db.session.rollback()
            flash("Could not save survey. Please try again.", "error")
        return redirect(url_for("playing.detail", pg_id=pg_id))

    return render_template("playing/finish_survey.html", game=pg)


@playing_bp.route("/<int:pg_id>/delete", methods=["POST"])
def delete(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()
    name = pg.name
    db.session.delete(pg)
    try:
        db.session.commit()
        flash(f"'{name}' removed.", "success")
        return redirect(url_for("playing.index"))
    except Exception:
        db.session.rollback()
        flash("Could not remove the game. Please try again.", "error")
        return redirect(url_for("playing.detail", pg_id=pg_id))
