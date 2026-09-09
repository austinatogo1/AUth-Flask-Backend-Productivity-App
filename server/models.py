from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

from config import bcrypt, db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    _password_hash = db.Column("password_hash", db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entries = db.relationship(
        "JournalEntry",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def password(self):
        """Hashes are write-only; reading one is always a bug."""
        raise AttributeError("Password hashes may not be viewed.")

    @password.setter
    def password(self, plaintext):
        if not plaintext or len(plaintext) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        self._password_hash = bcrypt.generate_password_hash(
            plaintext.encode("utf-8")
        ).decode("utf-8")

    def authenticate(self, plaintext):
        return bcrypt.check_password_hash(self._password_hash, plaintext.encode("utf-8"))

    @validates("username")
    def validate_username(self, key, username):
        if not username or not username.strip():
            raise ValueError("Username is required.")
        if len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return username.strip()

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"


class JournalEntry(db.Model):
    __tablename__ = "journal_entries"

    VALID_MOODS = ("happy", "neutral", "sad", "anxious", "excited", "tired")

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=False, default="neutral")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    user = db.relationship("User", back_populates="entries")

    @validates("title")
    def validate_title(self, key, title):
        if not title or not title.strip():
            raise ValueError("Title is required.")
        if len(title.strip()) > 120:
            raise ValueError("Title must be 120 characters or fewer.")
        return title.strip()

    @validates("content")
    def validate_content(self, key, content):
        if not content or not content.strip():
            raise ValueError("Content is required.")
        return content.strip()

    @validates("mood")
    def validate_mood(self, key, mood):
        if mood not in self.VALID_MOODS:
            raise ValueError(f"Mood must be one of: {', '.join(self.VALID_MOODS)}.")
        return mood

    def __repr__(self):
        return f"<JournalEntry {self.id}: {self.title}>"