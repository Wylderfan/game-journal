# ---------------------------------------------------------------------------
# Play-Next Scoring Weights
# Edit these values to tune how games are ranked on the Play Next page.
# ---------------------------------------------------------------------------

# Points per hype star (hype is 1–5, so max = HYPE_MULTIPLIER * 5)
HYPE_MULTIPLIER = 10

# Bonus for games that are part of a series you're actively playing through
SERIES_CONTINUITY_BONUS = 25

# Points awarded based on estimated play length (shorter = higher priority)
LENGTH_SCORES = {
    "Short":     20,
    "Medium":    10,
    "Long":       5,
    "Very Long":  0,
}

# Category rank bonus: rank 1 gets CAT_RANK_MAX pts, each subsequent rank
# loses CAT_RANK_STEP pts, bottoming out at 0.
# e.g. defaults → rank 1 = 30, rank 2 = 25, rank 3 = 20 … rank 7+ = 0
CAT_RANK_MAX  = 30
CAT_RANK_STEP =  5

# Mood match: dot product of game moods × profile mood preferences,
# scaled to a 0–MOOD_MAX_POINTS range.
# (Max raw dot product = 5 dimensions × 5 × 5 = 125)
MOOD_MAX_POINTS = 30

# Active-library status adjustments
STATUS_PLAYING_BONUS  =  30
STATUS_ON_HOLD_PENALTY = 15
