from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app import db
from app.models import Game, Category
from app.utils.helpers import _int

backlog_bp = Blueprint("backlog", __name__)

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

_LENGTH_SCORES = {"Short": 20, "Medium": 10, "Long": 5, "Very Long": 0}


def _play_next_score(game):
    """
    Compute a priority score for play-next ordering (higher = play sooner).

    Factors:
      - Hype (1–5 stars)               → 0–50 pts
      - Series continuity bonus         → +25 pts
      - Estimated length (shorter wins) → 0–20 pts
      - Category rank bonus             → rank 1 = +30, rank 2 = +25 … rank 7+ = 0
      - Status: Playing                 → +30 pts
      - Status: On Hold                 → –15 pts
    """
    score  = (game.hype or 0) * 10
    score += 25 if game.series_continuity else 0
    score += _LENGTH_SCORES.get(game.estimated_length or "", 0)

    if game.category and game.category.rank:
        score += max(0, 30 - (game.category.rank - 1) * 5)

    if game.status == "Playing":
        score += 30
    elif game.status == "On Hold":
        score -= 15

    return score


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@backlog_bp.route("/")
def index():
    categories = Category.query.order_by(Category.rank, Category.name).all()
    uncategorized = (
        Game.query
        .filter_by(section="backlog", category_id=None)
        .order_by(Game.name)
        .all()
    )
    return render_template(
        "backlog/index.html",
        categories=categories,
        uncategorized=uncategorized,
    )


@backlog_bp.route("/add", methods=["GET", "POST"])
def add():
    categories = Category.query.order_by(Category.rank, Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("backlog.add"))

        cat_id = _int(request.form.get("category_id"))

        game = Game(
            name=name,
            section="backlog",
            status=None,
            rank=0,
            category_id=cat_id,
            rawg_id=_int(request.form.get("rawg_id")),
            cover_url=request.form.get("cover_url") or None,
            release_year=_int(request.form.get("release_year")),
            genres=request.form.get("genres") or None,
            platforms=request.form.get("platforms") or None,
            # Survey fields
            hype=_int(request.form.get("hype")),
            estimated_length=request.form.get("estimated_length") or None,
            series_continuity=bool(request.form.get("series_continuity")),
            mood_chill=_int(request.form.get("mood_chill")),
            mood_intense=_int(request.form.get("mood_intense")),
            mood_story=_int(request.form.get("mood_story")),
            mood_action=_int(request.form.get("mood_action")),
            mood_exploration=_int(request.form.get("mood_exploration")),
        )
        db.session.add(game)

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
    # Backlog games + active games that are Playing or On Hold
    backlog_games = Game.query.filter_by(section="backlog").all()
    active_games = (
        Game.query
        .filter(Game.section == "active", Game.status.in_(["Playing", "On Hold"]))
        .all()
    )
    ranked = sorted(backlog_games + active_games, key=_play_next_score, reverse=True)
    return render_template("backlog/play_next.html", ranked=ranked)


@backlog_bp.route("/<int:game_id>/promote", methods=["POST"])
def promote(game_id):
    game = db.get_or_404(Game, game_id)
    game.section       = "active"
    game.status        = "Playing"
    game.rank          = 0
    game.play_next_rank = None
    try:
        db.session.commit()
        flash(f"'{game.name}' promoted to active library.", "success")
        return redirect(url_for("playing.index"))
    except Exception:
        db.session.rollback()
        flash("Could not promote the game. Please try again.", "error")
        return redirect(url_for("backlog.index"))


@backlog_bp.route("/<int:game_id>/delete", methods=["POST"])
def delete(game_id):
    game = db.get_or_404(Game, game_id)
    name = game.name
    db.session.delete(game)
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
    return render_template("backlog/categories.html", categories=all_cats)


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
