import os
import uuid

from flask import Flask
from sqlalchemy import select

from db.connection import db
from db.models import DeploymentVersion
from v1.statefulset import StatefulSet


class MyFlaskApp(Flask):

    def initialize(self):
        # setting up loggers
        self.logger.info("Checking for kubernetes migrations")
        create = {
            "k8s": [],
            "db": []
        }

        session = db.session.connection()
        for i in StatefulSet.MANIFEST:
            resource = i['kind']
            h = DeploymentVersion.hash_data(str(i))
            query = select(DeploymentVersion) \
                .where(DeploymentVersion.name == resource) \
                .where(DeploymentVersion.hash == h) \
                .limit(1)
            dep_version = session.execute(query).first()

            if not dep_version:
                create["k8s"].append(i)
                create["db"].append(DeploymentVersion(name=resource, hash=h))
                self.logger.info(f"Updating {resource}")
            else:
                self.logger.debug(f"Found {resource}")

        if create['db']:
            db.session.add_all(create["db"])
            db.session.commit()
            
        if create['k8s']:
            print(create['k8s'])
            for dep in StatefulSet.get_deployments():
                name = dep.metadata.name

                # update the deployment with the new files
                data = StatefulSet().setup(_id=name.split('-')[1], token=str(uuid.uuid4()))
                for item in create['k8s']:
                    new_data = data[item['kind']]
                    StatefulSet.patch(new_data, namespace='default')
    
    def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
        if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
            with self.app_context():
                self.initialize()
        super().run(host, port, debug, load_dotenv, **options)
