from datetime import datetime
from app import db


class Category(db.Model):
    __tablename__ = "categories"

    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    # Priority order for play-next scoring (1 = most interested in right now).
    rank = db.Column(db.Integer, nullable=False, default=0)

    # One category → many games, ordered alphabetically.
    # back_populates mirrors Game.category so both sides are explicit.
    games = db.relationship(
        "Game",
        back_populates="category",
        order_by="Game.name",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Category {self.name!r}>"


class Game(db.Model):
    __tablename__ = "games"

    # ------------------------------------------------------------------ #
    # Core identity                                                        #
    # ------------------------------------------------------------------ #
    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)

    # Which half of the app this game lives in.
    section = db.Column(
        db.Enum("active", "backlog", name="section_enum"),
        nullable=False,
    )

    # Lifecycle status — only meaningful for active games.
    status = db.Column(
        db.Enum("Playing", "On Hold", "Dropped", "Completed", name="status_enum"),
        nullable=True,
    )

    # ------------------------------------------------------------------ #
    # Personal tracking                                                    #
    # ------------------------------------------------------------------ #
    enjoyment  = db.Column(db.Integer, nullable=True)   # 1–5; null = unrated
    motivation = db.Column(db.Integer, nullable=True)   # 1–5; null = unrated
    notes      = db.Column(db.Text,    nullable=True)

    # ------------------------------------------------------------------ #
    # Backlog ordering                                                     #
    # ------------------------------------------------------------------ #
    rank = db.Column(db.Integer, nullable=False, default=0)

    # Cross-category play-next rank (1 = play first).  Null for games that
    # pre-date the feature or were added without the survey.
    play_next_rank = db.Column(db.Integer, nullable=True)

    # ------------------------------------------------------------------ #
    # Play-next survey (backlog only)                                      #
    # ------------------------------------------------------------------ #
    hype             = db.Column(db.Integer, nullable=True)   # 1–5
    estimated_length = db.Column(
        db.Enum("Short", "Medium", "Long", "Very Long", name="length_enum"),
        nullable=True,
    )
    series_continuity = db.Column(db.Boolean, nullable=True, default=False)

    # Mood blend sliders (0–5 each)
    mood_chill       = db.Column(db.Integer, nullable=True)
    mood_intense     = db.Column(db.Integer, nullable=True)
    mood_story       = db.Column(db.Integer, nullable=True)
    mood_action      = db.Column(db.Integer, nullable=True)
    mood_exploration = db.Column(db.Integer, nullable=True)

    # SET NULL so deleting a category orphans its games rather than
    # raising a foreign-key violation.
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    category = db.relationship("Category", back_populates="games")

    # ------------------------------------------------------------------ #
    # RAWG metadata (optional — populated at add time via API lookup)     #
    # ------------------------------------------------------------------ #
    rawg_id      = db.Column(db.Integer,     nullable=True)
    cover_url    = db.Column(db.String(500), nullable=True)
    release_year = db.Column(db.Integer,     nullable=True)
    genres       = db.Column(db.String(200), nullable=True)   # "RPG, Action"
    platforms    = db.Column(db.String(300), nullable=True)   # "PC, PS5"

    # ------------------------------------------------------------------ #
    # Finished-game survey                                                 #
    # ------------------------------------------------------------------ #
    finished         = db.Column(db.Boolean,  nullable=False, default=False)
    overall_rating   = db.Column(db.Integer,  nullable=True)   # 1–10
    would_play_again = db.Column(
        db.Enum("Yes", "No", "Maybe", name="wpa_enum"), nullable=True
    )
    hours_to_finish  = db.Column(db.Integer,  nullable=True)
    difficulty       = db.Column(db.Integer,  nullable=True)   # 1–5

    # ------------------------------------------------------------------ #
    # Timestamps                                                           #
    # ------------------------------------------------------------------ #
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Reverse relationship populated by CheckIn model below.
    checkins = db.relationship(
        "CheckIn",
        back_populates="game",
        order_by="CheckIn.created_at.desc()",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        """Serialise to a plain dict for JSON responses (e.g. reorder, search)."""
        return {
            "id":           self.id,
            "name":         self.name,
            "section":      self.section,
            "status":       self.status,
            "enjoyment":    self.enjoyment,
            "motivation":   self.motivation,
            "notes":        self.notes,
            "rank":         self.rank,
            "category_id":  self.category_id,
            "rawg_id":          self.rawg_id,
            "cover_url":        self.cover_url,
            "release_year":     self.release_year,
            "genres":           self.genres,
            "platforms":        self.platforms,
            "play_next_rank":   self.play_next_rank,
            "hype":             self.hype,
            "estimated_length": self.estimated_length,
            "series_continuity":self.series_continuity,
            "mood_chill":       self.mood_chill,
            "mood_intense":     self.mood_intense,
            "mood_story":       self.mood_story,
            "mood_action":      self.mood_action,
            "mood_exploration":  self.mood_exploration,
            "finished":          self.finished,
            "overall_rating":    self.overall_rating,
            "would_play_again":  self.would_play_again,
            "hours_to_finish":   self.hours_to_finish,
            "difficulty":        self.difficulty,
        }

    def __repr__(self) -> str:
        return f"<Game {self.name!r} [{self.section}/{self.status}]>"


class CheckIn(db.Model):
    __tablename__ = "checkins"

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id      = db.Column(
        db.Integer,
        db.ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    motivation   = db.Column(db.Integer, nullable=True)    # 1–5
    enjoyment    = db.Column(db.Integer, nullable=True)    # 1–5
    note         = db.Column(db.Text,    nullable=True)
    hours_played = db.Column(db.Numeric(5, 1), nullable=True)
    status       = db.Column(db.String(20),    nullable=True)
    created_at   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    game = db.relationship("Game", back_populates="checkins")

    def __repr__(self) -> str:
        return f"<CheckIn game_id={self.game_id} at={self.created_at}>"
