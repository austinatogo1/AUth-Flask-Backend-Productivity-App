from flask import jsonify

from config import api, app, db
from resources.auth import CheckSession, Login, Logout, Signup
from resources.entries import EntryById, EntryList

# Flask-Migrate can see them.
import models  # noqa: F401


@app.route("/")
def index():
    """Health check, useful for confirming the server is up."""
    return jsonify({"message": "Journal API is running."}), 200


@app.errorhandler(404)
def not_found(error):
    """Returns JSON for unknown URLs instead of Flask's HTML error page."""
    return jsonify({"error": "Resource not found."}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed for this endpoint."}), 405


@app.errorhandler(500)
def internal_error(error):
    """Rolls back the failed transaction so the session is not left dirty."""
    db.session.rollback()
    return jsonify({"error": "An internal server error occurred."}), 500


api.add_resource(Signup, "/signup")
api.add_resource(Login, "/login")
api.add_resource(CheckSession, "/check_session")
api.add_resource(Logout, "/logout")
api.add_resource(EntryList, "/entries")
api.add_resource(EntryById, "/entries/<int:id>")


if __name__ == "__main__":
    app.run(port=5555, debug=True)