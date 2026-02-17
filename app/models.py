from datetime import datetime
from app import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    games = db.relationship("Game", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    section = db.Column(db.Enum("active", "backlog"), nullable=False)
    status = db.Column(
        db.Enum("Playing", "On Hold", "Dropped", "Completed"), nullable=True
    )
    enjoyment = db.Column(db.Integer, nullable=True)   # 1–5
    motivation = db.Column(db.Integer, nullable=True)  # 1–5
    notes = db.Column(db.Text, nullable=True)
    rank = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Game {self.name}>"
