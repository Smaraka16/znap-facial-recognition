from flask import Flask

from flask_cors import CORS
import urllib.parse
from flask_sqlalchemy import SQLAlchemy

from datetime import timedelta


db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = "postgresql://postgres:1712@localhost:5432/news"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["EXECUTOR_TYPE"] = "thread"

    db.init_app(app)

    from Rwood.imageupload.routes import imageupload

    app.register_blueprint(imageupload)

    return app
