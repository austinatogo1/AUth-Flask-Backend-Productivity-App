"""Rubric audit for the Flask Auth Summative Lab.

Run from the server directory:  python rubric_check.py

Every check runs against this repository's own code. Nothing needs to be
running; an in-memory database is used, so app.db is never touched.
"""

import inspect
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER_DIR = os.path.dirname(os.path.abspath(__file__))

from app import app  # noqa: E402
from config import db  # noqa: E402
from models import JournalEntry, User  # noqa: E402

app.config["TESTING"] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

criteria = []


class Criterion:
    def __init__(self, name, points):
        self.name = name
        self.points = points
        self.checks = []
        criteria.append(self)

    def check(self, label, condition, detail=""):
        self.checks.append((label, bool(condition), detail))

    @property
    def passed(self):
        return all(ok for _, ok, _ in self.checks)

    @property
    def awarded(self):
        return self.points if self.passed else 0


def client_for(app_client):
    return app_client


def signup(c, username="alice", password="password123"):
    return c.post("/signup", json={"username": username, "password": password})


def entry(c, title="Test entry", content="Body text", mood="neutral"):
    return c.post("/entries", json={"title": title, "content": content, "mood": mood})


def read(path):
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        full = os.path.join(SERVER_DIR, path)
    if not os.path.exists(full):
        return ""
    with open(full, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def git(*args):
    try:
        return subprocess.run(
            ["git"] + list(args), cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
    except Exception:
        return ""


with app.app_context():
    db.create_all()

    # ---------------------------------------------------------------- 1
    c1 = Criterion("Auth (Login / Logout)", 10)
    with app.test_client() as c:
        signup(c, "loginuser")
        c.delete("/logout")
        c1.check("POST /login with valid credentials returns 200",
                 c.post("/login", json={"username": "loginuser",
                                        "password": "password123"}).status_code == 200)
        c.delete("/logout")
        c1.check("Wrong password returns 401",
                 c.post("/login", json={"username": "loginuser",
                                        "password": "bad"}).status_code == 401)
        c1.check("Unknown user returns 401",
                 c.post("/login", json={"username": "ghost",
                                        "password": "password123"}).status_code == 401)
        c1.check("Missing fields return 422",
                 c.post("/login", json={}).status_code == 422)
        c.post("/login", json={"username": "loginuser", "password": "password123"})
        c1.check("DELETE /logout returns 204", c.delete("/logout").status_code == 204)
        c1.check("Logout while logged out returns 401",
                 c.delete("/logout").status_code == 401)

    # ---------------------------------------------------------------- 2
    c2 = Criterion("Auth (Check Session / Me)", 10)
    with app.test_client() as c:
        c2.check("check_session returns 401 when logged out",
                 c.get("/check_session").status_code == 401)
        signup(c, "sessionuser")
        r = c.get("/check_session")
        c2.check("check_session returns 200 when logged in", r.status_code == 200)
        c2.check("Returns the correct user",
                 r.get_json().get("username") == "sessionuser", str(r.get_json()))
        c2.check("Session survives repeated requests (stays logged in on refresh)",
                 c.get("/check_session").status_code == 200
                 and c.get("/check_session").status_code == 200)
        c.delete("/logout")
        c2.check("Stays logged out after logout",
                 c.get("/check_session").status_code == 401)

    # ---------------------------------------------------------------- 3
    c3 = Criterion("Auth (Sign Up)", 10)
    with app.test_client() as c:
        r = signup(c, "brandnew")
        c3.check("POST /signup returns 201", r.status_code == 201, str(r.status_code))
        c3.check("User is persisted to the database",
                 User.query.filter_by(username="brandnew").first() is not None)
        c3.check("Response contains id and username",
                 "id" in (r.get_json() or {}) and "username" in (r.get_json() or {}))
        c3.check("Response leaks no password field",
                 "password" not in r.get_data(as_text=True).lower())
        c.delete("/logout")
        c3.check("Duplicate username returns 409", signup(c, "brandnew").status_code == 409)
        c3.check("Short password returns 422",
                 signup(c, "another", "abc").status_code == 422)
        c3.check("Missing password returns 422",
                 c.post("/signup", json={"username": "nopw"}).status_code == 422)

    # ---------------------------------------------------------------- 4
    c4 = Criterion("Auth (Model and Password Protection)", 10)
    with app.test_client() as c:
        signup(c, "hashcheck")
        u = User.query.filter_by(username="hashcheck").first()
        c4.check("Username column is unique",
                 User.__table__.columns["username"].unique is True)
        c4.check("Password stored as a bcrypt hash",
                 u._password_hash.startswith("$2b$") or u._password_hash.startswith("$2a$"),
                 u._password_hash[:10])
        c4.check("Hash differs from the plaintext", u._password_hash != "password123")
        try:
            u.password
            readable = True
        except AttributeError:
            readable = False
        c4.check("Reading .password raises AttributeError", not readable)
        c4.check("authenticate() accepts the correct password",
                 u.authenticate("password123"))
        c4.check("authenticate() rejects a wrong password",
                 not u.authenticate("wrongpassword"))
        c4.check("flask_bcrypt is used", "bcrypt" in read("server/config.py"))

    # ---------------------------------------------------------------- 5
    c5 = Criterion("Additional Resource (model)", 10)
    cols = set(JournalEntry.__table__.columns.keys())
    custom = cols - {"id", "user_id"}
    c5.check("Model has a user_id foreign key", "user_id" in cols)
    c5.check("Foreign key targets users.id",
             any("users.id" in str(fk.target_fullname)
                 for fk in JournalEntry.__table__.columns["user_id"].foreign_keys))
    c5.check(f"Has 2+ custom fields (found {len(custom)}: {', '.join(sorted(custom))})",
             len(custom) >= 2)
    c5.check("User.entries relationship is defined", hasattr(User, "entries"))
    c5.check("JournalEntry.user relationship is defined", hasattr(JournalEntry, "user"))
    with app.test_client() as c:
        uid = signup(c, "reluser").get_json()["id"]
        entry(c)
        owner = db.session.get(User, uid)
        c5.check("Relationship links entries to their owner", len(owner.entries) == 1)

    # ---------------------------------------------------------------- 6
    c6 = Criterion("Protected Routes", 10)
    with app.test_client() as anon:
        for method, path in [("get", "/entries"), ("post", "/entries"),
                             ("get", "/entries/1"), ("patch", "/entries/1"),
                             ("delete", "/entries/1")]:
            code = getattr(anon, method)(path, json={}).status_code
            c6.check(f"Unauthenticated {method.upper()} {path} returns 401",
                     code == 401, str(code))

    with app.test_client() as owner:
        signup(owner, "victim")
        victim_entry = entry(owner, title="Private thoughts").get_json()["id"]
    with app.test_client() as attacker:
        signup(attacker, "attacker")
        c6.check("Other user GET on foreign entry returns 404",
                 attacker.get(f"/entries/{victim_entry}").status_code == 404)
        c6.check("Other user PATCH on foreign entry returns 404",
                 attacker.patch(f"/entries/{victim_entry}",
                                json={"title": "Hacked"}).status_code == 404)
        c6.check("Other user DELETE on foreign entry returns 404",
                 attacker.delete(f"/entries/{victim_entry}").status_code == 404)
        c6.check("Foreign entry absent from other user's index",
                 attacker.get("/entries").get_json()["entries"] == [])
    with app.test_client() as owner2:
        owner2.post("/login", json={"username": "victim", "password": "password123"})
        r = owner2.get(f"/entries/{victim_entry}")
        c6.check("Owner can still read the entry", r.status_code == 200)
        c6.check("Entry was not modified by the attacker",
                 r.get_json()["title"] == "Private thoughts")

    # ---------------------------------------------------------------- 7
    c7 = Criterion("Code Structure & Maintainability", 5)
    for path in ["server/app.py", "server/config.py", "server/models.py",
                 "server/schemas.py", "server/utils.py", "server/seed.py",
                 "server/resources/auth.py", "server/resources/entries.py"]:
        c7.check(f"{path} exists", bool(read(path)))
    app_lines = len([l for l in read("server/app.py").splitlines() if l.strip()])
    c7.check(f"app.py is thin, not a single script ({app_lines} lines)", app_lines < 80)
    c7.check("Routes are split across resource modules",
             bool(read("server/resources/auth.py")) and bool(read("server/resources/entries.py")))
    c7.check("Auth guard is factored into a reusable decorator",
             "def login_required" in read("server/utils.py"))
    c7.check("Modules carry docstrings",
             all(read(p).lstrip().startswith('"""')
                 for p in ["server/models.py", "server/schemas.py", "server/utils.py"]))

    # ---------------------------------------------------------------- 8
    c8 = Criterion("README", 10)
    readme = read("README.md")
    lower = readme.lower()
    c8.check("README.md exists and is substantial",
             len(readme) > 500, f"{len(readme)} chars")
    c8.check("Has a title heading", readme.lstrip().startswith("#"))
    c8.check("Has a description section", "description" in lower or len(readme) > 800)
    c8.check("Documents installation (pipenv install)", "pipenv install" in lower)
    c8.check("Documents migrating the database", "flask db upgrade" in lower)
    c8.check("Documents seeding", "seed.py" in lower)
    c8.check("Documents how to run the server",
             "python app.py" in lower or "flask run" in lower)
    for route in ["/signup", "/login", "/check_session", "/logout", "/entries"]:
        c8.check(f"Documents the {route} endpoint", route in readme)
    c8.check("Documents status codes", "201" in readme and "401" in readme
             and "404" in readme and "422" in readme)

    # ---------------------------------------------------------------- 9
    c9 = Criterion("Seed File", 10)
    seed_src = read("server/seed.py")
    c9.check("seed.py exists", bool(seed_src))
    c9.check("Uses Faker", "faker" in seed_src.lower())
    c9.check("Wraps work in an app context", "app_context" in seed_src)
    User.query.delete()
    db.session.commit()
    sys.path.insert(0, SERVER_DIR)
    try:
        import seed as seed_module
        seed_module.seed_database()
        seeded_users = User.query.count()
        seeded_entries = JournalEntry.query.count()
        c9.check(f"Creates User records ({seeded_users})", seeded_users > 0)
        c9.check(f"Creates JournalEntry records ({seeded_entries})", seeded_entries > 0)
        c9.check("Seeds every model without error", seeded_users > 0 and seeded_entries > 0)
        c9.check("Entries are distributed across users",
                 len({e.user_id for e in JournalEntry.query.all()}) == seeded_users)
        c9.check("Enough entries to demonstrate pagination", seeded_entries > 10)
    except Exception as exc:  # noqa: BLE001
        c9.check("Seed script runs without error", False, repr(exc))

    # --------------------------------------------------------------- 10
    c10 = Criterion("Git Workflow & Management", 5)
    log = git("log", "--oneline", "-40")
    commits = [l for l in log.splitlines() if l.strip()]
    merges = git("log", "--merges", "--oneline", "-20").splitlines()
    c10.check(f"Repository has commits ({len(commits)})", len(commits) >= 4)
    c10.check(f"History contains merge commits from PRs ({len(merges)})", len(merges) >= 2)
    conventional = [l for l in commits
                    if re.search(r"\b(feat|fix|chore|docs|refactor|test)\b[:(]", l)]
    c10.check(f"Commit messages are descriptive ({len(conventional)}/{len(commits)} "
              f"conventional)", len(conventional) >= max(3, len(commits) // 2))
    c10.check("Current branch is main or a feature branch",
              git("rev-parse", "--abbrev-ref", "HEAD") != "HEAD")
    status = git("status", "--porcelain")
    c10.check("Working tree is clean (all work committed)",
              status == "", status[:200] or "clean")
    tracked = git("ls-files")
    c10.check("No database file committed",
              not re.search(r"\.db$|\.sqlite3$", tracked, re.M))
    c10.check("Migrations are committed", "migrations/versions/" in tracked)
    c10.check("Pipfile is committed", "Pipfile" in tracked)

    # --------------------------------------------------------------- 11
    c11 = Criterion("Resource CRUD Routes and Pagination", 10)
    with app.test_client() as c:
        signup(c, "cruduser")
        r = entry(c, title="Created entry")
        c11.check("POST /entries returns 201", r.status_code == 201, str(r.status_code))
        eid = r.get_json()["id"]
        c11.check("GET /entries/<id> returns 200",
                  c.get(f"/entries/{eid}").status_code == 200)
        r = c.patch(f"/entries/{eid}", json={"mood": "happy"})
        c11.check("PATCH /entries/<id> returns 200", r.status_code == 200)
        c11.check("PATCH actually updates the field", r.get_json()["mood"] == "happy")
        c11.check("PATCH leaves untouched fields alone",
                  r.get_json()["title"] == "Created entry")
        c11.check("Invalid data returns 422",
                  entry(c, mood="ecstatic").status_code == 422)
        c11.check("Missing required field returns 422",
                  c.post("/entries", json={"title": "no body"}).status_code == 422)

        for i in range(24):
            entry(c, title=f"Bulk {i}")
        r = c.get("/entries?page=1&per_page=10")
        body = r.get_json()
        c11.check("GET /entries returns 200", r.status_code == 200)
        c11.check("Index response includes pagination metadata", "pagination" in body)
        c11.check("Page size is honoured", len(body["entries"]) == 10,
                  str(len(body["entries"])))
        c11.check("total_pages is computed", body["pagination"]["total_pages"] >= 3)
        c11.check("has_next is True on page 1", body["pagination"]["has_next"] is True)
        page2 = c.get("/entries?page=2&per_page=10").get_json()
        c11.check("Page 2 returns different records",
                  not {e["id"] for e in body["entries"]} & {e["id"] for e in page2["entries"]})
        c11.check("has_prev is True on page 2", page2["pagination"]["has_prev"] is True)
        c11.check("Invalid pagination args return 400",
                  c.get("/entries?page=abc").status_code == 400)
        c11.check("DELETE /entries/<id> returns 204",
                  c.delete(f"/entries/{eid}").status_code == 204)
        c11.check("Deleted entry is gone",
                  c.get(f"/entries/{eid}").status_code == 404)

    db.session.remove()
    db.drop_all()


# -------------------------------------------------------------------- report
WIDTH = 78
print("=" * WIDTH)
print("RUBRIC AUDIT".center(WIDTH))
print("=" * WIDTH)

total = 0
possible = 0
for crit in criteria:
    total += crit.awarded
    possible += crit.points
    mark = "PASS" if crit.passed else "REVIEW"
    print(f"\n[{mark}] {crit.name} — {crit.awarded}/{crit.points}")
    for label, ok, detail in crit.checks:
        if ok:
            print(f"    ok    {label}")
        else:
            print(f"    FAIL  {label}" + (f"  ({detail})" if detail else ""))

print("\n" + "=" * WIDTH)
print(f"TOTAL: {total}/{possible}")
print("=" * WIDTH)
print("\nNote: 'Code Structure' and 'Git Workflow' are judged by a human.")
print("These checks confirm the mechanical parts only.")

sys.exit(0 if total == possible else 1)