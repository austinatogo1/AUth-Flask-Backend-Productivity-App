"""Database models for the Journal API."""

from datetime import datetime

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates

from config import bcrypt, db


class User(db.Model):
    """An account. Usernames are unique; passwords are stored only as hashes."""

    __tablename__ = "users"

    MIN_USERNAME_LENGTH = 3
    MIN_PASSWORD_LENGTH = 6

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    _password_hash = db.Column("password_hash", db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    entries = db.relationship(
        "JournalEntry",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @hybrid_property
    def password(self):
        """Write-only. Reading a password hash is always a mistake, so refuse."""
        raise AttributeError("Password hashes may not be viewed.")

    @password.setter
    def password(self, plaintext):
        """Hashes the plaintext with bcrypt before it ever reaches the database."""
        if not plaintext or len(plaintext) < self.MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {self.MIN_PASSWORD_LENGTH} characters long."
            )
        self._password_hash = bcrypt.generate_password_hash(
            plaintext.encode("utf-8")
        ).decode("utf-8")

    def authenticate(self, plaintext):
        """Returns True when the plaintext matches the stored hash."""
        return bcrypt.check_password_hash(self._password_hash, plaintext.encode("utf-8"))

    @validates("username")
    def validate_username(self, key, username):
        if not username or not username.strip():
            raise ValueError("Username is required.")
        stripped = username.strip()
        if len(stripped) < self.MIN_USERNAME_LENGTH:
            raise ValueError(
                f"Username must be at least {self.MIN_USERNAME_LENGTH} characters long."
            )
        if len(stripped) > 50:
            raise ValueError("Username must be 50 characters or fewer.")
        return stripped

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"


class JournalEntry(db.Model):
    """A journal entry belonging to exactly one user."""

    __tablename__ = "journal_entries"

    VALID_MOODS = ("happy", "neutral", "sad", "anxious", "excited", "tired")
    MAX_TITLE_LENGTH = 120

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20), nullable=False, default="neutral")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    user = db.relationship("User", back_populates="entries")

    @validates("title")
    def validate_title(self, key, title):
        if not title or not title.strip():
            raise ValueError("Title is required.")
        stripped = title.strip()
        if len(stripped) > self.MAX_TITLE_LENGTH:
            raise ValueError(
                f"Title must be {self.MAX_TITLE_LENGTH} characters or fewer."
            )
        return stripped

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
