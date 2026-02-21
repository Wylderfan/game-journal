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
