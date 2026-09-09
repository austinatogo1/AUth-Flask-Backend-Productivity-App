import os

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

# Alembic cannot alter constraints that SQLite left unnamed, so give every
# constraint a predictable name up front.
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.json.compact = False

# Session cookie hardening. HTTPONLY blocks JavaScript from reading the cookie,
# which limits the damage of an XSS bug in the client.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.json.compact = False  # makes the JSON responses easier to read in the browser

db = SQLAlchemy(metadata=metadata)
db.init_app(app)

migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
api = Api(app)

# supports_credentials lets the browser send and store the session cookie.
CORS(
    app,
    supports_credentials=True,
    origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
)