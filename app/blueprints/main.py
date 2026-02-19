import os
from flask import Blueprint, render_template, jsonify, request
from app.models import Game, Category

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    playing_count   = Game.query.filter_by(section="active",  status="Playing").count()
    on_hold_count   = Game.query.filter_by(section="active",  status="On Hold").count()
    backlog_count   = Game.query.filter_by(section="backlog").count()
    completed_count = Game.query.filter_by(status="Completed").count()

    # Top-ranked game per category (relationship already orders by rank)
    categories = Category.query.order_by(Category.name).all()
    top_backlog = [cat.games[0] for cat in categories if cat.games]

    return render_template(
        "main/index.html",
        playing_count=playing_count,
        on_hold_count=on_hold_count,
        backlog_count=backlog_count,
        completed_count=completed_count,
        top_backlog=top_backlog,
    )


@main_bp.route("/api/games/search")
def search():
    """RAWG game search — returns JSON for the add-game forms."""
    q = request.args.get("q", "").strip()
    if not q or not os.environ.get("RAWG_API_KEY"):
        return jsonify([])
    try:
        from app.utils.rawg import search_games
        results = search_games(q, page_size=8)
        return jsonify([
            {
                "id":           r.get("id"),
                "name":         r.get("name"),
                "cover_url":    r.get("background_image"),
                "release_year": (r.get("released") or "")[:4] or None,
                "genres":       ", ".join(g["name"] for g in (r.get("genres") or [])),
                "platforms":    ", ".join(
                    p["platform"]["name"]
                    for p in (r.get("platforms") or [])
                    if p.get("platform")
                ),
            }
            for r in results
        ])
    except Exception:
        return jsonify([])
