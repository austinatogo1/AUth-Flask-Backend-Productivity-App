from flask import jsonify

from config import api, app, db
import models  # registers the models with SQLAlchemy's metadata


@app.route("/")
def index():
    return jsonify({"message": "Journal API is running."}), 200


if __name__ == "__main__":
    app.run(port=5555, debug=True)