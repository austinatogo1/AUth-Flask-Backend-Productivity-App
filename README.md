# Journal API

A secure REST API backend for a personal journaling app, built with Flask.

## Description

This is the backend for a productivity tool where users keep private journal
entries. Users register and log in with a username and password, and each entry
belongs to exactly one account.

Authentication is **session-based**: on a successful signup or login the server
stores the user's id in a signed cookie, and every subsequent request is
identified by that cookie. Passwords are hashed with bcrypt and are never
returned by any endpoint.

Access control is enforced at the query level. Every lookup for a journal entry
is filtered by the authenticated user's id, so one account can never read,
update, or delete another account's entries — a request for someone else's
entry returns `404 Not Found` rather than `403 Forbidden`, so the API never
confirms that another user's record exists.

### Features

- Session authentication: signup, login, logout, and session check
- Passwords hashed with Flask-Bcrypt and stored as write-only attributes
- Unique usernames enforced at the database and validation layers
- Full CRUD for journal entries
- Pagination on the entry index, with a capped page size
- Every entry route protected and scoped to its owner
- Marshmallow schemas for input validation and output serialization
- Seed script using Faker
- Pytest suite covering auth, CRUD, pagination, and ownership isolation

### Tech stack

Python 3.8.13, Flask 2.2.2, Flask-SQLAlchemy 3.0.3, Flask-Migrate 4.0.0,
Flask-RESTful 0.3.9, Flask-Bcrypt 1.0.1, Marshmallow 3.20.1, Faker 15.3.2,
SQLite.

## Project structure

```
.
├── Pipfile
├── README.md
├── .env.example
└── server
    ├── app.py              # Entry point: route registration and error handlers
    ├── config.py           # Flask app, extensions, CORS, database config
    ├── models.py           # User and JournalEntry models
    ├── schemas.py          # Marshmallow serialization and validation
    ├── utils.py            # get_current_user and the login_required decorator
    ├── seed.py             # Database seeding with Faker
    ├── test_app.py         # Pytest suite
    ├── migrations/         # Alembic migrations
    └── resources
        ├── auth.py         # Signup, login, check_session, logout
        └── entries.py      # Journal entry CRUD and pagination
```

## Installation

Requires Python 3.8.13 and Pipenv.

```bash
git clone https://github.com/austinatogo1/AUth-Flask-Backend-Productivity-App.git
cd AUth-Flask-Backend-Productivity-App
pipenv install --dev
pipenv shell
```

Set up the database:

```bash
cd server
export FLASK_APP=app.py
flask db upgrade head
python seed.py
```

The seed script creates three demo accounts — `austin`, `jane`, and `sam` —
each with 25 entries and the password `password123`.

## Running the server

```bash
cd server
python app.py
```

The API runs at `http://localhost:5555`.

## Running the tests

```bash
cd server
pytest
```

## Environment variables

Both are optional; sensible development defaults are used when they are unset.

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs the session cookie | `dev-secret-key-change-in-production` |
| `DATABASE_URI` | SQLAlchemy connection string | `sqlite:///app.db` |

## API endpoints

All request and response bodies are JSON. Authenticated endpoints require the
session cookie, which the browser sends automatically once a user has signed up
or logged in. With curl, use a cookie jar: `-c cookies.txt` to save and
`-b cookies.txt` to send.

### Authentication

#### `POST /signup`

Creates a user account and logs them in immediately.

Body: `{ "username": "austin", "password": "password123" }`

| Status | Meaning |
| --- | --- |
| 201 | Account created; session started |
| 409 | Username already taken |
| 422 | Missing field, username under 3 characters, or password under 6 |

#### `POST /login`

Authenticates an existing user and starts a session.

Body: `{ "username": "austin", "password": "password123" }`

| Status | Meaning |
| --- | --- |
| 200 | Logged in |
| 401 | Invalid username or password |
| 422 | Username or password missing from the body |

#### `GET /check_session`

Returns the current user. The client calls this on page load to restore auth
state after a refresh.

| Status | Meaning |
| --- | --- |
| 200 | Returns the logged-in user |
| 401 | No active session |

#### `DELETE /logout`

Clears the session cookie.

| Status | Meaning |
| --- | --- |
| 204 | Logged out; no content returned |
| 401 | Not logged in |

### Journal entries

Every route below requires authentication and operates only on entries owned by
the logged-in user.

#### `GET /entries`

Returns the current user's entries, newest first, paginated.

Query parameters:

| Parameter | Default | Notes |
| --- | --- | --- |
| `page` | 1 | Must be a positive integer |
| `per_page` | 10 | Must be a positive integer; capped at 50 |

Example response:

```json
{
  "entries": [
    {
      "id": 12,
      "title": "First day back",
      "content": "Long day, good progress.",
      "mood": "tired",
      "created_at": "2026-09-09T09:14:22",
      "updated_at": "2026-09-09T09:14:22",
      "user_id": 1
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_items": 25,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

| Status | Meaning |
| --- | --- |
| 200 | Returns entries and pagination metadata |
| 400 | `page` or `per_page` is not a positive integer |
| 401 | Not logged in |

#### `POST /entries`

Creates an entry owned by the logged-in user.

Body: `{ "title": "First day back", "content": "Long day.", "mood": "tired" }`

`title` and `content` are required. `mood` is optional and defaults to
`neutral`; valid values are `happy`, `neutral`, `sad`, `anxious`, `excited`,
and `tired`. A `user_id` in the body is ignored — ownership always comes from
the session.

| Status | Meaning |
| --- | --- |
| 201 | Entry created |
| 401 | Not logged in |
| 422 | Missing or invalid field |

#### `GET /entries/<id>`

Returns a single entry.

| Status | Meaning |
| --- | --- |
| 200 | Returns the entry |
| 401 | Not logged in |
| 404 | Entry does not exist, or belongs to another user |

#### `PATCH /entries/<id>`

Updates one or more fields on an entry. Send only the fields you want changed.

Body: `{ "mood": "happy" }`

| Status | Meaning |
| --- | --- |
| 200 | Returns the updated entry |
| 401 | Not logged in |
| 404 | Entry does not exist, or belongs to another user |
| 422 | Invalid value, or no updatable fields supplied |

#### `DELETE /entries/<id>`

Deletes an entry.

| Status | Meaning |
| --- | --- |
| 204 | Deleted; no content returned |
| 401 | Not logged in |
| 404 | Entry does not exist, or belongs to another user |

### Utility

#### `GET /`

Health check. Returns `200` with a status message.

## Data model

```
User                          JournalEntry
----                          ------------
id            integer PK      id          integer PK
username      string unique   title       string(120)
password_hash string          content     text
created_at    datetime        mood        string(20)
                              created_at  datetime
                              updated_at  datetime
                              user_id     integer FK -> users.id
```

One user has many journal entries. Deleting a user cascades to their entries.

## Security notes

- Passwords are hashed with bcrypt before they reach the database. The `password`
  attribute on `User` raises `AttributeError` on read, so a hash cannot leak
  through serialization.
- Login failures return the same message whether the username or the password
  was wrong, so responses cannot be used to enumerate accounts.
- `user_id` is `dump_only` in the entry schema, so a client cannot assign an
  entry to another account by including it in a request body.
- `per_page` is capped at 50 so a large value cannot force the server to
  serialize the whole table.
- The session cookie is `HttpOnly` and `SameSite=Lax`.

## Connecting a frontend

CORS is configured with `supports_credentials=True` for
`http://localhost:3000` and `http://localhost:5173`. A client must send
requests with credentials included, for example
`fetch(url, { credentials: "include" })`, so the browser attaches the session
cookie.