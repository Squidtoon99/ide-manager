import json
import os

import kubernetes.dynamic.exceptions
import yaml
from flask import jsonify, request
from flask_restful import Resource
from kubernetes import config, dynamic
from kubernetes.client import Configuration, api_client
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException

try:
    config.load_incluster_config()
except ConfigException:
    config.load_kube_config(config_file=os.path.join(
        os.path.dirname(__file__), 'k8s', 'kubeconfig.yml'))

k8s_config = Configuration().get_default_copy()

api_client = api_client.ApiClient(configuration=k8s_config)
client = dynamic.DynamicClient(
    api_client
)
api = client.resources.get(api_version='apps/v1', kind='StatefulSet')


class StatefulSet(Resource):
    _id: str
    with open(os.path.join(os.path.dirname(__file__), 'k8s', 'deployments.yml'), 'r') as f:
        MANIFEST = list(yaml.safe_load_all(f))

    def setup(self, _id, *, token=None):
        deployments = {}

        def fmt_fn(s):
            return str(s).format(
                user=_id,
                token=token or os.urandom(16).hex()
            )

        for i in self.MANIFEST:
            x = {}

            self.fmt(i, x, fmt_fn)
            deployments[x['kind']] = x
        return deployments

    def fmt(self, src, dest, fn):
        for k, v in src.items():
            if isinstance(v, dict):
                dest[k] = {}
                self.fmt(v, dest[k], fn)
            elif isinstance(v, list):
                dest[k] = []
                for i in v:
                    if isinstance(i, dict):
                        dest[k].append({})
                        self.fmt(i, dest[k][-1], fn)
                    else:
                        if isinstance(i, str):
                            i = fn(i)
                        dest[k].append(i)
            elif isinstance(v, str):
                dest[k] = fn(v)
            else:
                dest[k] = v

    @staticmethod
    def deployment(_id):
        try:
            return api.get(name=f'vs-{_id}-demo', namespace='default')
        except ApiException:
            return None

    def start(self, _id, *, _local=False):
        # check if the deployment already exists if so scale it to 1 pod, otherwise create it
        created = []
        deployments = self.setup(_id)
        if (dep := self.deployment(_id)) is not None:
            if dep.status.readyReplicas == 1:
                d = {"status": "running"}
                if _local:
                    d['dep'] = dep
                return d
            deployment = deployments.get("StatefulSet")
            api.patch(name=f'vs-{_id}-demo',
                      namespace='default', body=deployment)
            created = ['StatefulSet']
        else:
            # Create all in deployments
            for dep in deployments.values():
                api_proxy = client.resources.get(
                    api_version=dep['apiVersion'], kind=dep['kind'])
                try:
                    api_proxy.create(body=dep, namespace='default')
                except dynamic.exceptions.ConflictError:
                    continue # already exists
                created.append(str(dep['kind']))
        return {"status": "starting", "created": created}

    def stop(self, _id):
        # Stop the pod by scaling to 0
        if self.deployment(_id) is None:
            return {"status": "stopped"}  # Can't stop if it's not running
        deployments = self.setup(_id)
        if (deployment := deployments.get("StatefulSet")) is not None:
            deployment['spec']['replicas'] = 0
            api.patch(name=f'vs-{_id}-demo',
                      namespace='default', body=deployment)
            return {"status": "stopped"}

    def get(self, deployment_id):
        print("DEP ID: ", deployment_id)
        if deployment := self.deployment(deployment_id):
            print("Found deployment: ", deployment, deployment.status)
            return json.loads(json.dumps(dict(iter(deployment.status)), default=lambda o: o.__dict__))
        return None

    def post(self, deployment_id):
        # get the action key from the request data
        action = request.get_json().get('action')
        if action == 'start':
            return jsonify(self.start(deployment_id))
        elif action == 'stop':
            return jsonify(self.stop(deployment_id))
        elif action == 'delete':
            return self.delete(deployment_id)
        else:
            return jsonify({"status": "error", "error": "invalid action"})

    @staticmethod
    def patch(resource, namespace='default'):
        name = resource['metadata']['name']
        api_proxy = client.resources.get(
            api_version=resource['apiVersion'], kind=resource['kind'])

        return api_proxy.patch(name=name, namespace=namespace, body=resource, content_type="application/merge-patch"
                                                                                           "+json")

    def put(self, deployment_id):
        # Update the deployment
        self.setup(deployment_id)
        if self.deployment(deployment_id) is None:
            return jsonify({"status": "error", "error": "deployment not found"})

        # Update all in deployments
        updated = []
        deployments = self.setup(deployment_id)
        for dep in deployments.values():
            api_proxy = client.resources.get(
                api_version=dep['apiVersion'], kind=dep['kind'])
            api_proxy.patch(name=f'vs-{deployment_id}-demo',
                            namespace='default', body=dep)
            updated.append(str(dep['kind']))
        return jsonify({"status": "updated", "updated": updated})

    def delete(self, deployment_id):
        # Cleanup all resources
        deleted = []

        for resource in self.setup(deployment_id).values():
            # Check if resource exists
            print(resource['kind'], resource.get("apiVersion"))
            try:
                api_proxy = client.resources.get(
                    api_version=resource['apiVersion'], kind=resource['kind']
                )
            except ApiException:
                continue
            name = resource['metadata']['name']
            print("name: ", name)

            try:
                api_proxy.get(name=name, namespace='default')
            except kubernetes.dynamic.exceptions.NotFoundError:
                continue
            else:
                print(name)
                api_proxy.delete(name=name, namespace='default')
                deleted.append(str(resource['kind']))
        print(deleted)
        return jsonify({"status": "deleted", "deleted": deleted})

    @classmethod
    def get_deployments(cls):
        deployments = []
        for deployment in api.get(namespace='default').items:
            print("deployment: ", deployment.metadata.name)
            if deployment.metadata.name.startswith("vs-"):
                deployments.append(deployment)
        return deployments  

    def set_token(self, id, token):
        deployments = self.setup(id, token=token)
        deployment = deployments.get("IngressRoute")
        deployment['spec']['routes'][0][
            'match'] = f'PathPrefix(`/app/{id}`)'
        # deployment['spec']['routes'][0][
        #     'match'] = f'PathPrefix(`/app/{id}`) && HeadersRegexp(`Cookie`, `proxy-token-{current_user.id}={token};`)'
        self.patch(deployment, namespace='default')
