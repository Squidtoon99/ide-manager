"""
Webserver to abstract creation and deletion of ide deployments

* WARNING: this release of kubernetes.client requires python 3.9+
"""
# Initialize environment variables
try:
    # noinspection PyUnresolvedReferences
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import base64
import os
import random

from flask import jsonify, make_response, render_template, redirect, url_for, flash, request
from flask_dance.consumer import oauth_error, oauth_authorized
from flask_dance.consumer.storage.sqla import SQLAlchemyStorage
from flask_dance.contrib.google import make_google_blueprint
from flask_login import LoginManager, login_required, logout_user, current_user, login_user
from flask_migrate import Migrate
from sqlalchemy import select

from db.connection import db, ma
from db.models import User, OAuth
from flask_cls import MyFlaskApp
from v1 import bp as v1
from v1.api import api
from v1.statefulset import StatefulSet

# wow
print("Hello World :D")

# create the app

app = MyFlaskApp(__name__, static_folder='static', template_folder='templates')
# type: ignore # configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ['DATABASE_URL']
# initialize the app with the extension
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.login_view = "google.login"

login_manager.init_app(app)
ma.init_app(app)
api.init_app(app)

blueprint = make_google_blueprint(
    client_id=os.environ['GOOGLE_CLIENT_ID'],
    client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
    scope=["profile", "email"],
    storage=SQLAlchemyStorage(OAuth, db.session, user=current_user)
)

app.register_blueprint(blueprint, url_prefix="/login")


def b64_encode(data: str) -> str:
    return base64.urlsafe_b64encode(bytes(data, 'utf-8')).decode('utf-8').replace('=', '').replace('+', '-').replace(
        '/', '_')


# Keeping this commented out in case I need it later (flask-login handles this automatically, but I can optimize it
# for speed) since data I have received from Google is guaranteed to be valid, I can skip the validation step
# noinspection PyArgumentList
@oauth_authorized.connect_via(blueprint)
def google_logged_in(google_bp, token):
    if not token: flash("Failed to login.", category="error")

    resp = google_bp.session.get("/oauth2/v2/userinfo")
    if not resp.ok:
        msg = "Failed to fetch user info."
        flash(msg, category="error")
        return False

    info = resp.json()

    oauth = OAuth.query.filter_by(provider=google_bp.name, provider_email=info["email"]).first()
    if oauth is None:
        # noinspection PyArgumentList
        oauth = OAuth(provider=google_bp.name, provider_email=info["email"], token=token)

    if not oauth.user:
        user = User.query.filter_by(email=info["email"]).first()
        if user is None:
            user = User(email=info["email"], name=info["name"], image=info["picture"], is_teacher=False, school_id=1)
        oauth.user = user
        db.session.add_all([oauth, user])
        db.session.commit()
        flash("Successfully signed in.")

    login_user(oauth.user)
    return False


@oauth_error.connect_via(blueprint)
def google_error(blueprint_2, message, response):
    msg = "OAuth error from {name}! message={message} response={response}".format(
        name=blueprint_2.name, message=message, response=response
    )
    flash(msg, category="error")


@login_manager.user_loader
def load_user(user_id):
    # noinspection PyTypeChecker
    s = select(User).where(User.id == user_id)
    return db.session.execute(s).scalar()


@login_manager.unauthorized_handler
def unauthorized():
    # if request.blueprint in ["v1", "v2", "v3"]:
    return make_response(jsonify({"error": "Unauthorized"}), 401)

app.secret_key = os.getenv("SECRET_KEY", "supersekrit")

app.register_blueprint(v1)


@app.errorhandler(404)
def http_404(_e):
    return jsonify({"error": "not found"}), 404


def is_valid(deployment: str):
    return deployment in ['server', 'arjun']


@app.route("/api/v1/deployments/<deployment>/token-bypass", methods=["POST"])
def rust_shutdown(deployment: int):
    if request.headers['Authentication'] != str(app.secret_key):
        return jsonify({"Authentication token required"}), 401

    return StatefulSet().stop(deployment)


@app.route("/app/<deployment>/", methods=['GET'])
@login_required
def cold_boot(deployment):
    if current_user.id != int(deployment):
        return make_response(jsonify({"error": f"Unauthorized {current_user.id}-{deployment}"}), 401)
    dep = StatefulSet()

    data = dep.start(deployment, _local=True)
    response = make_response(render_template('loading.html', name=deployment))
    print("data: ", data)
    if data.get("status") == "running":
        random.seed(current_user.id)
        token = b64_encode(f'{deployment}:{random.randint(0, 1000000)}')
        response.set_cookie(f'proxy-token-{current_user.id}', token)
        dep.set_token(current_user.id, token)

    response.headers['X-Served-By'] = 'flask'

    return response


@app.route("/")
def index():
    return "Hello World 👋"


@app.route("/login", methods=['GET'])
def login():
    return redirect(url_for('google.login'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# this is the actual debugging statement
if __name__ == '__main__':
    print("XYZ")
    app.run(debug=True, port=8000)
