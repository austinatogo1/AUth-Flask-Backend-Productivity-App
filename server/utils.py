from functools import wraps

from flask import session

from models import User


def get_current_user():
    """Returns the logged-in User, or None if the session is empty or stale."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(func):
    """Rejects unauthenticated requests with 401 before the view runs."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            return {"error": "Unauthorized. Please log in."}, 401
        return func(*args, **kwargs)

    return wrapper