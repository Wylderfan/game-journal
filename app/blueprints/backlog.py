from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from app import db
from app.models import Game, Category

backlog_bp = Blueprint("backlog", __name__)


def _int(value):
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


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


@backlog_bp.route("/<int:game_id>/promote", methods=["POST"])
def promote(game_id):
    game = db.get_or_404(Game, game_id)
    game.section     = "active"
    game.status      = "Playing"
    game.rank        = 0
    game.category_id = None
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
