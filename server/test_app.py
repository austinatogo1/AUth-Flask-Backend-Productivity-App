"""Automated tests for the Journal API.

Run with `pytest` from the server directory. Each test runs against a fresh
in-memory SQLite database, so the tests never touch app.db.
"""

import pytest

from app import app
from config import db
from models import JournalEntry, User


@pytest.fixture
def client():
    """Yields a test client backed by a throwaway in-memory database."""
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        with app.test_client() as test_client:
            yield test_client
        db.session.remove()
        db.drop_all()


def signup(client, username="alice", password="password123"):
    return client.post("/signup", json={"username": username, "password": password})


def make_entry(client, title="Test entry", content="Body text", mood="neutral"):
    return client.post("/entries", json={"title": title, "content": content, "mood": mood})


# --- Auth -------------------------------------------------------------------

def test_signup_creates_user_and_returns_201(client):
    response = signup(client)
    assert response.status_code == 201
    assert response.json["username"] == "alice"
    assert "password" not in response.json


def test_signup_rejects_duplicate_username(client):
    signup(client)
    client.delete("/logout")
    assert signup(client).status_code == 409


def test_signup_rejects_short_password(client):
    assert signup(client, password="abc").status_code == 422


def test_password_is_hashed_not_stored_plaintext(client):
    signup(client)
    user = User.query.filter_by(username="alice").first()
    assert user._password_hash != "password123"
    assert user._password_hash.startswith("$2b$")


def test_password_attribute_cannot_be_read(client):
    signup(client)
    user = User.query.filter_by(username="alice").first()
    with pytest.raises(AttributeError):
        user.password


def test_login_succeeds_with_correct_credentials(client):
    signup(client)
    client.delete("/logout")
    response = client.post("/login", json={"username": "alice", "password": "password123"})
    assert response.status_code == 200


def test_login_fails_with_wrong_password(client):
    signup(client)
    client.delete("/logout")
    response = client.post("/login", json={"username": "alice", "password": "nope"})
    assert response.status_code == 401


def test_check_session_returns_user_when_logged_in(client):
    signup(client)
    assert client.get("/check_session").status_code == 200


def test_check_session_returns_401_when_logged_out(client):
    assert client.get("/check_session").status_code == 401


def test_logout_clears_the_session(client):
    signup(client)
    assert client.delete("/logout").status_code == 204
    assert client.get("/check_session").status_code == 401


# --- Route protection -------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("get", "/entries"),
    ("post", "/entries"),
    ("get", "/entries/1"),
    ("patch", "/entries/1"),
    ("delete", "/entries/1"),
])
def test_entry_routes_require_authentication(client, method, path):
    response = getattr(client, method)(path, json={})
    assert response.status_code == 401


# --- CRUD -------------------------------------------------------------------

def test_create_entry_returns_201_and_assigns_owner(client):
    user_id = signup(client).json["id"]
    response = make_entry(client)
    assert response.status_code == 201
    assert response.json["user_id"] == user_id


def test_create_entry_rejects_invalid_mood(client):
    signup(client)
    assert make_entry(client, mood="ecstatic").status_code == 422


def test_create_entry_requires_content(client):
    signup(client)
    assert client.post("/entries", json={"title": "No body"}).status_code == 422


def test_supplied_user_id_is_ignored(client):
    user_id = signup(client).json["id"]
    response = client.post("/entries", json={
        "title": "Injection", "content": "Body", "user_id": 9999})
    assert response.status_code == 201
    assert response.json["user_id"] == user_id


def test_patch_updates_only_supplied_fields(client):
    signup(client)
    entry_id = make_entry(client, title="Original").json["id"]
    response = client.patch(f"/entries/{entry_id}", json={"mood": "happy"})
    assert response.status_code == 200
    assert response.json["mood"] == "happy"
    assert response.json["title"] == "Original"


def test_delete_removes_the_entry(client):
    signup(client)
    entry_id = make_entry(client).json["id"]
    assert client.delete(f"/entries/{entry_id}").status_code == 204
    assert client.get(f"/entries/{entry_id}").status_code == 404


# --- Pagination -------------------------------------------------------------

def test_index_paginates_results(client):
    signup(client)
    for i in range(25):
        make_entry(client, title=f"Entry {i}")

    response = client.get("/entries?page=1&per_page=10")
    assert response.status_code == 200
    assert len(response.json["entries"]) == 10
    assert response.json["pagination"]["total_items"] == 25
    assert response.json["pagination"]["total_pages"] == 3
    assert response.json["pagination"]["has_next"] is True
    assert response.json["pagination"]["has_prev"] is False


def test_per_page_is_capped(client):
    signup(client)
    make_entry(client)
    response = client.get("/entries?per_page=100000")
    assert response.json["pagination"]["per_page"] == 50


def test_invalid_pagination_args_return_400(client):
    signup(client)
    assert client.get("/entries?page=abc").status_code == 400
    assert client.get("/entries?page=0").status_code == 400


# --- Ownership isolation ----------------------------------------------------

def test_users_cannot_read_or_modify_each_others_entries(client):
    signup(client, username="alice")
    entry_id = make_entry(client, title="Alice's entry").json["id"]
    client.delete("/logout")

    signup(client, username="mallory")
    assert client.get(f"/entries/{entry_id}").status_code == 404
    assert client.patch(f"/entries/{entry_id}", json={"title": "Hacked"}).status_code == 404
    assert client.delete(f"/entries/{entry_id}").status_code == 404

    # Mallory's index must not leak Alice's entry either.
    assert client.get("/entries").json["entries"] == []

    client.delete("/logout")
    client.post("/login", json={"username": "alice", "password": "password123"})
    assert client.get(f"/entries/{entry_id}").json["title"] == "Alice's entry"


def test_deleting_a_user_cascades_to_their_entries(client):
    signup(client)
    make_entry(client)
    user = User.query.filter_by(username="alice").first()
    db.session.delete(user)
    db.session.commit()
    assert JournalEntry.query.count() == 0