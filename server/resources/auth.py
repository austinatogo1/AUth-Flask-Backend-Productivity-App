"""Session-based authentication endpoints."""

from flask import request, session
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError

from config import db
from models import User
from schemas import user_schema
from utils import get_current_user, login_required


class Signup(Resource):
    """POST /signup - creates an account and starts a session immediately."""

    def post(self):
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return {"error": "Username and password are required."}, 422

        try:
            user = User(username=username)
            user.password = password  # triggers the bcrypt hashing setter
            db.session.add(user)
            db.session.commit()
        except ValueError as error:
            db.session.rollback()
            return {"error": str(error)}, 422
        except IntegrityError:
            db.session.rollback()
            return {"error": "That username is already taken."}, 409

        # without it a new account is bounced straight back to the login screen.
        session["user_id"] = user.id
        return user_schema.dump(user), 201


class Login(Resource):
    """POST /login - verifies credentials and starts a session."""

    def post(self):
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return {"error": "Username and password are required."}, 422

        user = User.query.filter_by(username=username).first()

        # A single vague message for both failure modes, so responses cannot be
        # used to enumerate which usernames exist.
        if not user or not user.authenticate(password):
            return {"error": "Invalid username or password."}, 401

        session["user_id"] = user.id
        return user_schema.dump(user), 200


class CheckSession(Resource):
    """GET /check_session - lets the client restore auth state after a refresh.

    This route is intentionally not decorated with login_required: answering
    "am I logged in?" requires handling the logged-out case itself.
    """

    def get(self):
        user = get_current_user()
        if not user:
            return {"error": "Unauthorized. Please log in."}, 401
        return user_schema.dump(user), 200


class Logout(Resource):
    """DELETE /logout - clears the session cookie."""

    @login_required
    def delete(self):
        session.pop("user_id", None)
        return {}, 204