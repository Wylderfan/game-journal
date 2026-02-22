import os
from flask import Blueprint, render_template, jsonify, request, session, redirect, current_app
from app.models import ProfileGame, MoodPreferences
from app.utils.helpers import current_profile

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    profile = current_profile()

    playing_count   = ProfileGame.query.filter_by(profile_id=profile, section="active",  status="Playing").count()
    on_hold_count   = ProfileGame.query.filter_by(profile_id=profile, section="active",  status="On Hold").count()
    backlog_count   = ProfileGame.query.filter_by(profile_id=profile, section="backlog").count()
    completed_count = ProfileGame.query.filter_by(profile_id=profile, status="Completed").count()

    # Top 5 games from the dynamic play-next scoring
    from app.blueprints.backlog import _play_next_score
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
    play_next = sorted(backlog_pgs + active_pgs, key=lambda pg: _play_next_score(pg, prefs), reverse=True)[:5]

    return render_template(
        "main/index.html",
        playing_count=playing_count,
        on_hold_count=on_hold_count,
        backlog_count=backlog_count,
        completed_count=completed_count,
        play_next=play_next,
    )


@main_bp.route("/switch-profile", methods=["POST"])
def switch_profile():
    profiles = current_app.config["PROFILES"]
    name = request.form.get("profile", "").strip()
    if name in profiles:
        session["profile"] = name
    return redirect(request.referrer or "/")


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
