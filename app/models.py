from datetime import datetime
from app import db

STATUSES = ["Playing", "On Hold", "Dropped", "Completed"]


class Category(db.Model):
    __tablename__ = "categories"

    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    # Priority order for play-next scoring (1 = most interested in right now).
    rank = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Category {self.name!r}>"


class Game(db.Model):
    """Shared game record — RAWG metadata only. Per-profile data lives in ProfileGame."""
    __tablename__ = "games"

    id           = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    name         = db.Column(db.String(200), nullable=False)
    rawg_id      = db.Column(db.Integer,     nullable=True, unique=True)
    cover_url    = db.Column(db.String(500), nullable=True)
    release_year = db.Column(db.Integer,     nullable=True)
    genres       = db.Column(db.String(200), nullable=True)   # "RPG, Action"
    platforms    = db.Column(db.String(300), nullable=True)   # "PC, PS5"
    created_at   = db.Column(db.DateTime,   nullable=False, default=datetime.utcnow)

    # One game can have many per-profile entries (one per profile that tracks it).
    profile_games = db.relationship(
        "ProfileGame",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "name":         self.name,
            "rawg_id":      self.rawg_id,
            "cover_url":    self.cover_url,
            "release_year": self.release_year,
            "genres":       self.genres,
            "platforms":    self.platforms,
        }

    def __repr__(self) -> str:
        return f"<Game {self.name!r}>"


class ProfileGame(db.Model):
    """Per-profile tracking data for a game."""
    __tablename__ = "profile_games"

    id         = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    profile_id = db.Column(db.String(100),  nullable=False)
    game_id    = db.Column(db.Integer,      db.ForeignKey("games.id", ondelete="CASCADE"), nullable=False)

    # ------------------------------------------------------------------ #
    # Library placement                                                    #
    # ------------------------------------------------------------------ #
    section = db.Column(
        db.Enum("active", "backlog", name="pg_section_enum"),
        nullable=False,
    )
    status = db.Column(
        db.Enum("Playing", "On Hold", "Dropped", "Completed", name="pg_status_enum"),
        nullable=True,
    )
    rank           = db.Column(db.Integer, nullable=False, default=0)
    play_next_rank = db.Column(db.Integer, nullable=True)

    # ------------------------------------------------------------------ #
    # Play-next survey                                                     #
    # ------------------------------------------------------------------ #
    hype             = db.Column(db.Integer, nullable=True)
    estimated_length = db.Column(
        db.Enum("Short", "Medium", "Long", "Very Long", name="pg_length_enum"),
        nullable=True,
    )
    series_continuity = db.Column(db.Boolean, nullable=True, default=False)

    mood_chill       = db.Column(db.Integer, nullable=True)
    mood_intense     = db.Column(db.Integer, nullable=True)
    mood_story       = db.Column(db.Integer, nullable=True)
    mood_action      = db.Column(db.Integer, nullable=True)
    mood_exploration = db.Column(db.Integer, nullable=True)

    # ------------------------------------------------------------------ #
    # Personal tracking                                                    #
    # ------------------------------------------------------------------ #
    notes = db.Column(db.Text, nullable=True)

    # ------------------------------------------------------------------ #
    # Finished-game survey                                                 #
    # ------------------------------------------------------------------ #
    finished         = db.Column(db.Boolean, nullable=False, default=False)
    overall_rating   = db.Column(db.Integer, nullable=True)
    would_play_again = db.Column(
        db.Enum("Yes", "No", "Maybe", name="pg_wpa_enum"), nullable=True
    )
    hours_to_finish = db.Column(db.Integer, nullable=True)
    difficulty      = db.Column(db.Integer, nullable=True)

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

    # ------------------------------------------------------------------ #
    # Relationships                                                        #
    # ------------------------------------------------------------------ #
    game = db.relationship("Game", back_populates="profile_games")

    # checkins relationship added in issue #47
    # categories M2M relationship added in issue #46

    # ------------------------------------------------------------------ #
    # Proxy properties — delegate RAWG/identity fields to the Game row    #
    # so templates use pg.name, pg.cover_url, etc. without changes.      #
    # ------------------------------------------------------------------ #
    @property
    def name(self):
        return self.game.name

    @property
    def cover_url(self):
        return self.game.cover_url

    @property
    def release_year(self):
        return self.game.release_year

    @property
    def genres(self):
        return self.game.genres

    @property
    def platforms(self):
        return self.game.platforms

    @property
    def rawg_id(self):
        return self.game.rawg_id

    @property
    def categories(self):
        # Placeholder until issue #46 adds per-profile M2M
        return []

    def __repr__(self) -> str:
        return f"<ProfileGame profile={self.profile_id!r} game={self.game_id} [{self.section}/{self.status}]>"


class MoodPreferences(db.Model):
    """Singleton row storing the user's current mood-dimension weights for play-next scoring."""
    __tablename__ = "mood_preferences"

    id               = db.Column(db.Integer, primary_key=True, default=1)
    mood_chill       = db.Column(db.Integer, nullable=False, default=0)
    mood_intense     = db.Column(db.Integer, nullable=False, default=0)
    mood_story       = db.Column(db.Integer, nullable=False, default=0)
    mood_action      = db.Column(db.Integer, nullable=False, default=0)
    mood_exploration = db.Column(db.Integer, nullable=False, default=0)

    @classmethod
    def get(cls):
        """Return the singleton row, creating it if it doesn't exist."""
        prefs = cls.query.first()
        if prefs is None:
            prefs = cls(id=1)
            db.session.add(prefs)
            db.session.commit()
        return prefs


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

    def __repr__(self) -> str:
        return f"<CheckIn game_id={self.game_id} at={self.created_at}>"
