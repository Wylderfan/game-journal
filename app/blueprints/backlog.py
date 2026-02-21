from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app import db
from app.models import Game, Category

backlog_bp = Blueprint("backlog", __name__)

# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _int(value):
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


_LENGTH_SCORES = {"Short": 20, "Medium": 10, "Long": 5, "Very Long": 0}


def _play_next_score(hype, estimated_length, series_continuity):
    """Compute a priority score for play-next ordering (higher = play sooner)."""
    score  = (hype or 0) * 10                                    # 0–50
    score += 25 if series_continuity else 0                      # 0 or 25
    score += _LENGTH_SCORES.get(estimated_length or "", 0)       # 0–20
    return score  # max 95


def _assign_initial_play_next_rank(new_game):
    """
    Insert *new_game* into the global play-next list at the position that
    matches its score.  Shifts all subsequent games' ranks up by 1.
    """
    new_score = _play_next_score(
        new_game.hype, new_game.estimated_length, new_game.series_continuity
    )

    ranked = (
        Game.query
        .filter(Game.section == "backlog", Game.play_next_rank.isnot(None), Game.id != new_game.id)
        .order_by(Game.play_next_rank)
        .all()
    )

    insert_at = len(ranked)  # default: append at end
    for i, g in enumerate(ranked):
        if _play_next_score(g.hype, g.estimated_length, g.series_continuity) < new_score:
            insert_at = i
            break

    for g in ranked[insert_at:]:
        g.play_next_rank = g.play_next_rank + 1

    new_game.play_next_rank = insert_at + 1


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@backlog_bp.route("/")
def index():
    categories = Category.query.order_by(Category.name).all()
    uncategorized = (
        Game.query
        .filter_by(section="backlog", category_id=None)
        .order_by(Game.rank)
        .all()
    )
    return render_template(
        "backlog/index.html",
        categories=categories,
        uncategorized=uncategorized,
    )


@backlog_bp.route("/add", methods=["GET", "POST"])
def add():
    categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Game name is required.", "error")
            return redirect(url_for("backlog.add"))

        cat_id = _int(request.form.get("category_id"))

        # Place new game at the bottom of its category
        max_rank = (
            db.session.query(db.func.max(Game.rank))
            .filter_by(section="backlog", category_id=cat_id)
            .scalar()
        ) or 0

        game = Game(
            name=name,
            section="backlog",
            status=None,
            rank=max_rank + 1,
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
        _assign_initial_play_next_rank(game)

        try:
            db.session.commit()
            flash(f"'{game.name}' added to backlog.", "success")
            return redirect(url_for("backlog.index"))
        except Exception:
            db.session.rollback()
            flash("Something went wrong. Please try again.", "error")
            return redirect(url_for("backlog.add"))

    return render_template("backlog/add.html", categories=categories)


@backlog_bp.route("/reorder", methods=["POST"])
def reorder():
    """Receives an ordered list of game IDs and updates their rank fields."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, list):
        return jsonify({"error": "invalid payload"}), 400

    try:
        for rank, game_id in enumerate(data):
            Game.query.filter_by(id=game_id).update({"rank": rank})
        db.session.commit()
        return jsonify({"ok": True})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "reorder failed"}), 500


@backlog_bp.route("/play-next")
def play_next():
    ranked = (
        Game.query
        .filter(Game.section == "backlog", Game.play_next_rank.isnot(None))
        .order_by(Game.play_next_rank)
        .all()
    )
    unranked = (
        Game.query
        .filter(Game.section == "backlog", Game.play_next_rank.is_(None))
        .order_by(Game.name)
        .all()
    )
    return render_template("backlog/play_next.html", ranked=ranked, unranked=unranked)


@backlog_bp.route("/play-next/reorder", methods=["POST"])
def play_next_reorder():
    """Receives an ordered list of game IDs and updates their play_next_rank fields."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, list):
        return jsonify({"error": "invalid payload"}), 400

    try:
        for rank, game_id in enumerate(data, start=1):
            Game.query.filter_by(id=game_id).update({"play_next_rank": rank})
        db.session.commit()
        return jsonify({"ok": True})
    except Exception:
        db.session.rollback()
        return jsonify({"error": "reorder failed"}), 500


@backlog_bp.route("/<int:game_id>/promote", methods=["POST"])
def promote(game_id):
    game = db.get_or_404(Game, game_id)
    game.section       = "active"
    game.status        = "Playing"
    game.rank          = 0
    game.category_id   = None
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
            db.session.add(Category(name=name))
            try:
                db.session.commit()
                flash(f"Category '{name}' created.", "success")
            except Exception:
                db.session.rollback()
                flash("Could not create category. Please try again.", "error")
        return redirect(url_for("backlog.categories"))

    all_cats = Category.query.order_by(Category.name).all()
    return render_template("backlog/categories.html", categories=all_cats)


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
