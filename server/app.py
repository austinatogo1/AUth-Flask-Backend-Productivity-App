from flask import jsonify

from config import api, app, db
from resources.auth import CheckSession, Login, Logout, Signup
import models  # registers the models with SQLAlchemy's metadata


@app.route("/")
def index():
    return jsonify({"message": "Journal API is running."}), 200

api.add_resource(Signup, "/signup")
api.add_resource(Login, "/login")
api.add_resource(CheckSession, "/check_session")
api.add_resource(Logout, "/logout")

if __name__ == "__main__":
    app.run(port=5555, debug=True)