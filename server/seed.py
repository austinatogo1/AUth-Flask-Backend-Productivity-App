"""Seeds the database with demo users and journal entries.

Run from the server directory with `python seed.py`.
"""

from random import choice

from faker import Faker

from app import app
from config import db
from models import JournalEntry, User

fake = Faker()

# Shared password across demo accounts keeps manual testing simple.
DEMO_USERS = [
    ("austin", "password123"),
    ("jane", "password123"),
    ("sam", "password123"),
]

# 25 entries each means three pages at the default page size, so has_next and
# has_prev both have something to demonstrate.
ENTRIES_PER_USER = 25


def seed_database():
    print("Clearing existing data...")
    JournalEntry.query.delete()
    User.query.delete()
    db.session.commit()

    print("Seeding users...")
    users = []
    for username, password in DEMO_USERS:
        user = User(username=username)
        user.password = password
        users.append(user)
    db.session.add_all(users)
    db.session.commit()

    print("Seeding journal entries...")
    entries = []
    for user in users:
        for _ in range(ENTRIES_PER_USER):
            entries.append(
                JournalEntry(
                    title=fake.sentence(nb_words=4).rstrip("."),
                    content=fake.paragraph(nb_sentences=5),
                    mood=choice(JournalEntry.VALID_MOODS),
                    user_id=user.id,
                )
            )
    db.session.add_all(entries)
    db.session.commit()

    print(f"Done. Created {len(users)} users and {len(entries)} entries.")
    print("Log in with any of: " + ", ".join(name for name, _ in DEMO_USERS))
    print("Password for all demo accounts: password123")


if __name__ == "__main__":
    # SQLAlchemy needs an active application context to know which database to
    # talk to; without this the script raises "Working outside of application
    # context".
    with app.app_context():
        seed_database()