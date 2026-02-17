"""
RAWG API helpers.

Docs: https://rawg.io/apidocs
Free tier: 20,000 requests/month with an API key.

Set RAWG_API_KEY in your .env file.
"""

import os
import requests

RAWG_BASE = "https://api.rawg.io/api"


def _key():
    key = os.environ.get("RAWG_API_KEY")
    if not key:
        raise RuntimeError("RAWG_API_KEY is not set in environment")
    return key


def search_games(query, page_size=10):
    """
    Search RAWG for games matching *query*.

    Returns a list of result dicts, each containing:
        id, name, released, background_image, genres, platforms, metacritic
    """
    resp = requests.get(
        f"{RAWG_BASE}/games",
        params={"key": _key(), "search": query, "page_size": page_size},
        timeout=8,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])


def get_game(rawg_id):
    """
    Fetch full detail for a single game by its RAWG id.

    Returns the raw RAWG game dict.
    """
    resp = requests.get(
        f"{RAWG_BASE}/games/{rawg_id}",
        params={"key": _key()},
        timeout=8,
    )
    resp.raise_for_status()
    return resp.json()


def extract_metadata(rawg_game):
    """
    Pull the fields we store from a RAWG game dict (search result or detail).

    Returns a plain dict ready to unpack into a Game model:
        rawg_id, cover_url, release_year, genres, platforms
    """
    released = rawg_game.get("released") or ""
    year = int(released[:4]) if len(released) >= 4 else None

    genres = ", ".join(g["name"] for g in rawg_game.get("genres") or [])

    # Search results use "platforms" as a list of {"platform": {"name": ...}}
    # Detail endpoint uses the same shape
    raw_platforms = rawg_game.get("platforms") or []
    platforms = ", ".join(
        p["platform"]["name"] for p in raw_platforms if p.get("platform")
    )

    return {
        "rawg_id": rawg_game.get("id"),
        "cover_url": rawg_game.get("background_image"),
        "release_year": year,
        "genres": genres or None,
        "platforms": platforms or None,
    }
