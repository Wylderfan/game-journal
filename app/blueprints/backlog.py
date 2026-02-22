from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app import db
from app.models import Game, ProfileGame, Category, MoodPreferences
from app.utils.helpers import _int, current_profile

backlog_bp = Blueprint("backlog", __name__)

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

_LENGTH_SCORES = {"Short": 20, "Medium": 10, "Long": 5, "Very Long": 0}


def _play_next_score(pg, prefs=None):
    """
    Compute a priority score for play-next ordering (higher = play sooner).

    Factors:
      - Motivation & Excitement (1–5)   → 0–50 pts
      - Series continuity bonus         → +25 pts
      - Estimated length (shorter wins) → 0–20 pts
      - Category rank bonus             → rank 1 = +30, rank 2 = +25 … rank 7+ = 0
      - Mood match (dot product scaled) → 0–30 pts
      - Status: Playing                 → +30 pts
      - Status: On Hold                 → –15 pts
    """
    score  = (pg.hype or 0) * 10
    score += 25 if pg.series_continuity else 0
    score += _LENGTH_SCORES.get(pg.estimated_length or "", 0)

    if pg.categories:
        best_rank = min((c.rank for c in pg.categories if c.rank), default=0)
        if best_rank:
            score += max(0, 30 - (best_rank - 1) * 5)

    if prefs:
        dot = (
            (pg.mood_chill       or 0) * (prefs.mood_chill       or 0) +
            (pg.mood_intense     or 0) * (prefs.mood_intense     or 0) +
            (pg.mood_story       or 0) * (prefs.mood_story       or 0) +
            (pg.mood_action      or 0) * (prefs.mood_action      or 0) +
            (pg.mood_exploration or 0) * (prefs.mood_exploration or 0)
        )
        # Max dot product = 5 dims × 5 × 5 = 125; scale to 0–30 pts
        score += int((dot / 125) * 30)

    if pg.status == "Playing":
        score += 30
    elif pg.status == "On Hold":
        score -= 15

    return score


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@backlog_bp.route("/")
def index():
    profile = current_profile()
    categories = Category.query.order_by(Category.rank, Category.name).all()
    has_games = ProfileGame.query.filter_by(profile_id=profile, section="backlog").count() > 0
    # All backlog games shown as uncategorized until #46 restores per-profile M2M
    uncategorized = (
        ProfileGame.query
        .filter_by(profile_id=profile, section="backlog")
        .join(ProfileGame.game)
        .order_by(Game.name)
        .all()
    )
    return render_template(
        "backlog/index.html",
        categories=[],          # category grouping restored in #46
        uncategorized=uncategorized,
        has_games=has_games,
    )


@backlog_bp.route("/add", methods=["GET", "POST"])
def add():
    profile = current_profile()
    categories = Category.query.order_by(Category.rank, Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("backlog.add"))

        rawg_id = _int(request.form.get("rawg_id"))

        # Reuse existing Game row if rawg_id already known; else create new one
        if rawg_id:
            game = Game.query.filter_by(rawg_id=rawg_id).first()
        else:
            game = None

        if game is None:
            game = Game(
                name=name,
                rawg_id=rawg_id,
                cover_url=request.form.get("cover_url") or None,
                release_year=_int(request.form.get("release_year")),
                genres=request.form.get("genres") or None,
                platforms=request.form.get("platforms") or None,
            )
            db.session.add(game)
            db.session.flush()  # get game.id

        # Duplicate check: has this profile already added this game?
        existing = ProfileGame.query.filter_by(profile_id=profile, game_id=game.id).first()
        if existing:
            flash(f"'{game.name}' is already in your library.", "error")
            return redirect(url_for("backlog.add"))

        pg = ProfileGame(
            profile_id=profile,
            game_id=game.id,
            section="backlog",
            status=None,
            rank=0,
            hype=_int(request.form.get("hype")),
            estimated_length=request.form.get("estimated_length") or None,
            series_continuity=bool(request.form.get("series_continuity")),
            mood_chill=_int(request.form.get("mood_chill")),
            mood_intense=_int(request.form.get("mood_intense")),
            mood_story=_int(request.form.get("mood_story")),
            mood_action=_int(request.form.get("mood_action")),
            mood_exploration=_int(request.form.get("mood_exploration")),
        )
        db.session.add(pg)

        try:
            db.session.commit()
            flash(f"'{game.name}' added to backlog.", "success")
            return redirect(url_for("backlog.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("backlog.add"))

    return render_template("backlog/add.html", categories=categories)


@backlog_bp.route("/play-next")
def play_next():
    profile = current_profile()
    prefs = MoodPreferences.get()
    backlog_pgs = ProfileGame.query.filter_by(profile_id=profile, section="backlog").all()
    active_pgs = (
        ProfileGame.query
        .filter(
            ProfileGame.profile_id == profile,
            ProfileGame.section == "active",
            ProfileGame.status.in_(["Playing", "On Hold"]),
        )
        .all()
    )
    ranked = sorted(backlog_pgs + active_pgs, key=lambda pg: _play_next_score(pg, prefs), reverse=True)
    scores = {pg.id: _play_next_score(pg, prefs) for pg in ranked}
    return render_template("backlog/play_next.html", ranked=ranked, scores=scores)


@backlog_bp.route("/<int:pg_id>/edit", methods=["GET", "POST"])
def edit(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile, section="backlog").first_or_404()
    categories = Category.query.order_by(Category.rank, Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("backlog.edit", pg_id=pg_id))

        # Per-profile fields on ProfileGame
        pg.notes             = request.form.get("notes", "").strip() or None
        pg.hype              = _int(request.form.get("hype"))
        pg.estimated_length  = request.form.get("estimated_length") or None
        pg.series_continuity = bool(request.form.get("series_continuity"))
        pg.mood_chill        = _int(request.form.get("mood_chill"))
        pg.mood_intense      = _int(request.form.get("mood_intense"))
        pg.mood_story        = _int(request.form.get("mood_story"))
        pg.mood_action       = _int(request.form.get("mood_action"))
        pg.mood_exploration  = _int(request.form.get("mood_exploration"))

        # RAWG/identity fields on the shared Game row
        pg.game.name         = name
        pg.game.cover_url    = request.form.get("cover_url")    or pg.game.cover_url
        pg.game.rawg_id      = _int(request.form.get("rawg_id")) or pg.game.rawg_id
        pg.game.release_year = _int(request.form.get("release_year")) or pg.game.release_year
        pg.game.genres       = request.form.get("genres")        or pg.game.genres
        pg.game.platforms    = request.form.get("platforms")     or pg.game.platforms

        try:
            db.session.commit()
            flash(f"'{pg.name}' updated.", "success")
            return redirect(url_for("backlog.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("backlog.edit", pg_id=pg_id))

    return render_template("backlog/edit.html", game=pg, categories=categories)


@backlog_bp.route("/<int:pg_id>/promote", methods=["POST"])
def promote(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()
    pg.section        = "active"
    pg.status         = "Playing"
    pg.rank           = 0
    pg.play_next_rank = None
    try:
        db.session.commit()
        flash(f"'{pg.name}' promoted to active library.", "success")
        return redirect(url_for("playing.index"))
    except Exception:
        db.session.rollback()
        flash("Could not promote the game. Please try again.", "error")
        return redirect(url_for("backlog.index"))


@backlog_bp.route("/<int:pg_id>/delete", methods=["POST"])
def delete(pg_id):
    profile = current_profile()
    pg = ProfileGame.query.filter_by(id=pg_id, profile_id=profile).first_or_404()
    name = pg.name
    db.session.delete(pg)
    try:
        db.session.commit()
        flash(f"'{name}' removed from backlog.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not remove the game. Please try again.", "error")
    return redirect(url_for("backlog.index"))


@backlog_bp.route("/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            max_rank = db.session.query(db.func.max(Category.rank)).scalar() or 0
            db.session.add(Category(name=name, rank=max_rank + 1))
            try:
                db.session.commit()
                flash(f"Category '{name}' created.", "success")
            except Exception:
                db.session.rollback()
                flash("Could not create category. Please try again.", "error")
        return redirect(url_for("backlog.categories"))

    all_cats = Category.query.order_by(Category.rank, Category.name).all()
    prefs = MoodPreferences.get()
    return render_template("backlog/categories.html", categories=all_cats, prefs=prefs)


@backlog_bp.route("/categories/mood-preferences", methods=["POST"])
def save_mood_preferences():
    prefs = MoodPreferences.get()
    prefs.mood_chill       = _int(request.form.get("mood_chill"))       or 0
    prefs.mood_intense     = _int(request.form.get("mood_intense"))     or 0
    prefs.mood_story       = _int(request.form.get("mood_story"))       or 0
    prefs.mood_action      = _int(request.form.get("mood_action"))      or 0
    prefs.mood_exploration = _int(request.form.get("mood_exploration")) or 0
    try:
        db.session.commit()
        flash("Mood preferences saved.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not save mood preferences.", "error")
    return redirect(url_for("backlog.categories"))


@backlog_bp.route("/categories/reorder", methods=["POST"])
def categories_reorder():
    """Receives an ordered list of category IDs and updates their rank fields."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, list):
        return jsonify({"error": "invalid payload"}), 400

    try:
        for rank, cat_id in enumerate(data, start=1):
            Category.query.filter_by(id=cat_id).update({"rank": rank})
        db.session.commit()
        return jsonify({"ok": True})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "reorder failed"}), 500


@backlog_bp.route("/categories/<int:cat_id>/rename", methods=["POST"])
def rename_category(cat_id):
    cat = db.get_or_404(Category, cat_id)
    name = request.form.get("name", "").strip()
    if name:
        cat.name = name
        try:
            db.session.commit()
            flash(f"Category renamed to '{name}'.", "success")
        except Exception:
            db.session.rollback()
            flash("Could not rename category. Please try again.", "error")
    return redirect(url_for("backlog.categories"))


@backlog_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
def delete_category(cat_id):
    cat = db.get_or_404(Category, cat_id)
    name = cat.name
    db.session.delete(cat)
    try:
        db.session.commit()
        flash(f"Category '{name}' deleted. Its games are now uncategorized.", "success")
    except Exception:
        db.session.rollback()
        flash("Could not delete category. Please try again.", "error")
    return redirect(url_for("backlog.categories"))
