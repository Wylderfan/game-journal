def current_profile():
    """Return the active profile name from the session, defaulting to the first profile."""
    from flask import session, current_app
    profiles = current_app.config["PROFILES"]
    p = session.get("profile")
    return p if p in profiles else profiles[0]


def _int(value):
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


def _float(value):
    try:
        return float(value) if value else None
    except (ValueError, TypeError):
        return None
