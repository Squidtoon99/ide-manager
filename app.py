"""
Webserver to abstract creation and deletion of ide deployments

* WARNING: this release of kubernetes.client requires python 3.9+
"""
import json
import os

import yaml
from flask import Flask, jsonify, make_response, render_template, request, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_required, logout_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin, SQLAlchemyStorage
import base64
from kubernetes import config, dynamic
from kubernetes.client import Configuration, api_client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
from db.models import Course, School, User, Assignment, Project
from db.connection import db, ma

from v1 import bp as v1
from v1.api import api
# wow
print("Hello World :D")

# Initialize environment variables
try:
    # noinspection PyUnresolvedReferences
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
# create the app

app = Flask(__name__, static_folder='static', template_folder='templates')
# type: ignore # configure the SQLite database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ['DATABASE_URL']
# initialize the app with the extension
db.init_app(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
ma.init_app(app)
api.init_app(app)

blueprint = make_google_blueprint(
    client_id=os.environ['GOOGLE_CLIENT_ID'],
    client_secret=os.environ['GOOGLE_CLIENT_SECRET'],
    scope=["profile", "email"]
)


class OAuth(OAuthConsumerMixin, db.Model):  # type: ignore
    pass


blueprint.storage = SQLAlchemyStorage(OAuth, db.session)


app.register_blueprint(blueprint, url_prefix="/login")


def b64_encode(data: str) -> str:
    return base64.urlsafe_b64encode(bytes(data, 'utf-8')).decode('utf-8')


@login_manager.user_loader
def load_user(user_id):
    print("loading user %s" % user_id)
    return User.query.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    # if request.blueprint in ["v1", "v2", "v3"]:
    return make_response(jsonify({"error": "Unauthorized"}), 401)
    # return redirect(url_for("google.login", state=b64_encode(request.url)))

@login_manager.request_loader
def loader(request):
    if google.authorized:
        ... # TODO: FINISH
app.secret_key = "supersekrit"

app.register_blueprint(v1)

try:
    config.load_incluster_config()
except ConfigException:
    config.load_kube_config(config_file=os.path.join(
        os.path.dirname(__file__), 'kubeconfig.yml'))


k8s_config = Configuration().get_default_copy()

client = dynamic.DynamicClient(
    api_client.ApiClient(configuration=k8s_config)
)


class Deployment(object):
    name: str
    with open(os.path.join(os.path.dirname(__file__), 'deployments.yml'), 'r') as f:
        MANIFEST = list(yaml.safe_load_all(f))

    def __init__(self, name: str):
        assert "{" not in name and "}" not in name  # prevent injection
        self.api = client.resources.get(
            api_version="apps/v1", kind="Deployment")
        self.name = name
        self.deployments = {}
        self.setup()

    def setup(self):
        self.deployments.clear()
        for i in self.MANIFEST:
            x = {}
            self.fmt(i, x)
            self.deployments[x['kind']] = x

    def fmt(self, src, dest):
        for k, v in src.items():
            if isinstance(v, dict):
                dest[k] = {}
                self.fmt(v, dest[k])
            elif isinstance(v, list):
                dest[k] = []
                for i in v:
                    if isinstance(i, dict):
                        dest[k].append({})
                        self.fmt(i, dest[k][-1])
                    else:
                        if isinstance(i, str):
                            i = i.replace("{user}", self.name)
                        dest[k].append(i)
            elif isinstance(v, str):
                dest[k] = v.replace("{user}", self.name)
            else:
                dest[k] = v

    def deployment(self):
        try:
            return self.api.get(name=f'vs-{self.name}-demo', namespace='default')
        except ApiException:
            return None

    # returns the status of the deployment
    def status(self):
        if (deployment := self.deployment()) is None:
            return None
        return deployment.status

    def start(self):
        # check if the deployment already exists if so scale it to 1 pod, otherwise create it
        created = []
        if self.deployment() is not None:
            deployment = self.deployments.get("Deployment")
            self.api.patch(name=f'vs-{self.name}-demo',
                           namespace='default', body=deployment)
            created = ['Deployment']
        else:
            # Create all in deployments
            for dep in self.deployments.values():
                api = client.resources.get(
                    api_version=dep['apiVersion'], kind=dep['kind'])
                api.create(body=dep, namespace='default')
                created.append(str(dep['kind']))
        return {"status": "starting", "created": created}

    def stop(self):
        # Stop the pod by scaling to 0
        if (deployment := self.deployment()) is None:
            return {"status": "stopped"}  # Can't stop if it's not running

        if (deployment := self.deployments.get("Deployment")) is not None:
            deployment['spec']['replicas'] = 0
            self.api.patch(name=f'vs-{self.name}-demo',
                           namespace='default', body=deployment)
            return {"status": "stopped"}

    def delete(self):
        # Cleanup all resources
        deleted = []
        for resource in self.deployments.values():
            # Check if resource exists
            try:
                api = client.resources.get(
                    api_version=resource['apiVersion'], kind=resource['kind'])
            except ApiException:
                continue
            name = resource['metadata']['name']
            if api.get(name=name, namespace='default') is not None:
                api.delete(name=name, namespace='default')
                deleted.append(str(resource['kind']))
        return {"status": "deleted", "deleted": deleted}


d = Deployment("server")


@ app.route("/api/v1/@me")
def http_from_headers():
    # read the cookie formatted vs-{user}=.+; from the request headers
    cookies = request.headers.get('Cookie')
    if cookies:
        for c in cookies.split(";"):
            if c.startswith("vs-"):
                user = c.split('=')[0][3:]
                return http_status(user)
    return jsonify({"status": "not found", "availableReplicas": 0, "readyReplicas": 0, "replicas": 0}), 404


@ app.route('/api/v1/<deployment>/', methods=['POST', 'GET', 'DELETE'])
def http_status(deployment: str):
    """
    Get the status of a deployment
    """
    dep = Deployment(deployment)
    if request.method == "GET":
        if status := dep.status():
            resp = json.loads(json.dumps(dict(iter(status)),
                                         default=lambda o: o.__dict__))
            return jsonify(resp), 200
        return jsonify({"status": "not found", "availableReplicas": 0, "readyReplicas": 0, "replicas": 0}), 404
    elif request.method == "POST":
        data = request.get_json()
        if not data or not data.get('action'):
            return jsonify({"error": "invalid json"}), 400
        if data['action'] == "start":
            return jsonify(dep.start())
        elif data['action'] == "stop":
            return jsonify(dep.stop())
        elif data['action'] == "delete":
            return jsonify(dep.delete())
        else:
            return jsonify({"error": "invalid action"}), 400
    elif request.method == "DELETE":
        return jsonify(dep.delete()), 200
    else:
        return jsonify({"error": "invalid method"}), 405


def is_valid(deployment: str):
    return deployment in ['server', 'arjun']


@ app.route("/app/<deployment>/", methods=['GET'])
def cold_boot(deployment):
    if not is_valid(deployment):
        return jsonify({"error": "invalid deployment"}), 400
    dep = Deployment(deployment)

    dep.start()
    response = make_response(render_template('loading.html', name=deployment))
    response.headers['X-Served-By'] = 'flask'
    response.set_cookie(f'vs-{deployment}', 'true')
    return response


@app.route("/")
def index():
    return "Hello World 👋"


@ app.route("/login", methods=['GET'])
def login():
    return redirect(url_for('google.login'))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


# this is the actual debugging statement
if __name__ == '__main__':
    app.run(debug=True, port=8000)
