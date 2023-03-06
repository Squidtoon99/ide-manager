import re
from functools import wraps
from os import getenv
from typing import Union, Literal
from urllib.parse import urlencode

import requests
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from flask_restful import Resource, Api

from db.connection import db
from db.models import User, School, Course, Assignment, Project, File, Unit
from db.schemas import user_schema, school_schema, course_schema, assignment_schema, project_schema, file_schema, \
    unit_schema
from .statefulset import StatefulSet


def revalidate_path(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        data = current_app.ensure_sync(func)(*args, **kwargs)
        if path := request.headers.get('X-Forwarded-Path'):
            try:
                requests.get(request.host_url +
                             f"/cache/revalidate?secret={getenv('SECRET_KEY')}&path={urlencode(path)}",
                             timeout=1)
            except requests.exceptions.ReadTimeout:
                pass
        return data

    return wrapper


def better_login_required(func):
    secure = login_required(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated and (auth := request.headers.get('Authorization')):
            try:
                user_id, secret = auth.split(":")
                user = User.query.get(user_id)
                if user and user.secret == secret:
                    return func(*args, **kwargs)
            except ValueError:
                pass
        return secure(*args, **kwargs)

    return wrapper


api = Api(prefix="/api/v1/", decorators=[better_login_required])

bp = Blueprint('v1', __name__, url_prefix='/api/v1',
               template_folder='templates')

VALID_NAME = re.compile(r'^\w+$')
VALID_EMAIL = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
VALID_IMAGE = re.compile(r'^https?://.+')

"""
User {
    id,
    name,
    slug,
    email,
    image,
    
    is_teacher,
    school_id
}
"""


@bp.route("/users/@me")
@login_required
def user_profile(user):
    return jsonify(user)


@bp.route('/users/<_id>', methods=['GET'])
@login_required
def get_user(auth, _id: int):
    print(auth)
    user = User.query.get(_id)
    return jsonify(user)


@bp.route('/users/<_id>', methods=['DELETE'])
def delete_user(_id: int):
    user = User.query.get(_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify(user)


def validate_user(data: dict) -> Union[dict, Literal[False]]:
    for key in ['name', 'email', 'image', 'id']:
        if key not in data:
            return False
    if _id := data.get("_id"):
        if not isinstance(_id, int):
            return False
    if name := data.get('name'):
        if not VALID_NAME.match(name):
            return False
    if email := data.get('email'):
        if not VALID_EMAIL.match(email):
            return False
    if image := data.get('image'):
        if not VALID_IMAGE.match(image):
            return False
    return data


@bp.route("/users/<_id>", methods=['POST'])
def create_user(_id: int):
    if data := validate_user({"id": _id, **(request.json or {})}):
        user = User(**data)
        db.session.add(user)
        db.session.commit()
        return jsonify(user)
    else:
        return jsonify({'error': 'invalid data'}), 400


# SQLAlchemy Resources

class UserResource(Resource):
    @staticmethod
    def get(user_id):
        user = User.query.get_or_404(user_id)
        return user_schema.dump(user)

    @staticmethod
    def delete(user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return user_schema.dump(user)


class SelfResource(Resource):
    @staticmethod
    def get():
        return user_schema.dump(current_user)


class CourseResource(Resource):
    @staticmethod
    def get(course_id):
        course = Course.query.get_or_404(course_id)
        return course_schema.dump(course)


class SchoolResource(Resource):
    @staticmethod
    def get(school_id):
        school = School.query.get_or_404(school_id)
        return school_schema.dump(school)


class AssignmentResource(Resource):
    @staticmethod
    def get(course_id, assignment_id):
        assignment = Assignment.query.filter_by(
            course_id=course_id, id=assignment_id).first_or_404()
        return assignment_schema.dump(assignment)


class AssignmentResourceCreator(Resource):
    # Create a new assignment
    @staticmethod
    def get(course_id):
        assignments = Assignment.query.filter_by(course_id=course_id).all()
        return assignment_schema.dump(assignments, many=True)

    @staticmethod
    def post(course_id):
        data = request.json or {}
        data.setdefault('course_id', course_id)
        if data.get('course_id') != course_id:
            return {'error': 'invalid course id'}, 400
        assignment = Assignment.initialize(**data)
        db.session.add(assignment)
        db.session.commit()
        return assignment_schema.dump(assignment)


class CourseAssignmentsResource(Resource):
    @staticmethod
    def get(course_id: int):
        assignments = Assignment.query.filter_by(course_id=course_id).all()
        return assignment_schema.dump(assignments, many=True)


class UnitResource(Resource):
    @staticmethod
    def get(course_id, unit_id):
        unit = Unit.query.filter_by(course_id=course_id, id=unit_id).first_or_404()
        return unit_schema.dump(unit)

    @staticmethod
    def delete(course_id, unit_id):
        unit = Unit.query.filter_by(course_id=course_id, id=unit_id).first_or_404()
        db.session.delete(unit)
        db.session.commit()
        return unit_schema.dump(unit)

    @staticmethod
    def put(course_id, unit_id):
        data = request.json or {}
        unit = Unit.query.filter_by(course_id=course_id, id=unit_id).first_or_404()
        for key, value in data.items():
            setattr(unit, key, value)
        db.session.commit()
        return unit_schema.dump(unit)


class UnitListResource(Resource):
    @staticmethod
    def get(course_id):
        units = Unit.query.filter_by(course_id=course_id).all()
        return unit_schema.dump(units, many=True)

    @staticmethod
    def delete(course_id):
        units = Unit.query.filter_by(course_id=course_id).all()
        for unit in units:
            db.session.delete(unit)
        db.session.commit()
        return unit_schema.dump(units, many=True)

    @staticmethod
    def post(course_id):
        data = request.json or {}
        if data.get('id'):
            del data['id']

        if len(data.get("name", "")) == 0 or len(data.get("name", "")) > 100:
            return jsonify({'error': 'invalid data'}), 400
        data['course_id'] = course_id

        unit = Unit(**data)
        db.session.add(unit)
        db.session.commit()
        return unit_schema.dump(unit)


class ProjectResource(Resource):
    @staticmethod
    def get(project_id):
        project = Project.query.get_or_404(project_id)
        return project_schema.dump(project)


class UserProjectsResource(Resource):
    @staticmethod
    def get(user_id):
        if user_id == "@me":
            user_id = current_user.id
        else:
            if not user_id.isdigit():
                return jsonify({'error': 'invalid data'}), 400
            user_id = int(user_id)
        projects = Project.query.filter_by(user_id=user_id).all()
        return project_schema.dump(projects, many=True)


class FileResource(Resource):
    @staticmethod
    def get(file_id):
        f = File.query.get_or_404(file_id)
        return file_schema.dump(f)


class QuickDeployResource(Resource):
    @staticmethod
    def get(course_id, assignment_id):
        u_id = current_user.id
        assignment = Assignment.query.filter_by(
            course_id=course_id, id=assignment_id).first_or_404()
        project = Project.query.filter_by(
            assignment_id=assignment_id, user_id=u_id, blueprint=False).first()

        d = StatefulSet()
        print("fetching: ", current_user.id, flush=True)
        deployment_data = d.get(current_user.id)
        if not deployment_data:
            return d.start(current_user.id)

        if not project:
            # ensure the deployment is running before creating a project
            try:
                data = requests.get(
                    f"http://vs-{current_user.id}-svc.default.svc.cluster.local:3000/"
                )
                assert data.ok
            except requests.exceptions.ConnectionError:
                d.start(current_user.id)
                return {'error': 'deployment not ready'}, 400
            except AssertionError:
                return {'error': 'deployment not ready'}, 400
            project = Project.initialize(assignment=assignment, user=current_user)
        return project_schema.dump(project)


class QuickFileSyncResource(Resource):
    @staticmethod
    def get(user_id):
        if user_id == "@me":
            user_id = current_user.id
        else:
            if not user_id.isdigit():
                return jsonify({'error': 'invalid data'}), 400
            user_id = int(user_id)

        files = File.query.filter_by(user_id=user_id, sync=False).all()

        return file_schema.dump(files, many=True)

    @staticmethod
    def post(user_id):
        if user_id == "@me":
            user_id = current_user.id
        else:
            if not user_id.isdigit():
                return jsonify({'error': 'invalid data'}), 400
            user_id = int(user_id)
        data = request.json or {}
        if not data.get('file_id') or not data.get('file_id').isdigit():
            return jsonify({'error': 'invalid data'}), 400
        f = File.query.get_or_404(data['file_id'])
        if f.user_id != user_id:
            return jsonify({'error': 'invalid data'}), 400
        f.sync = True
        db.session.commit()
        return file_schema.dump(f)


api.add_resource(UserResource, '/users/<int:user_id>')
api.add_resource(SelfResource, '/users/@me')

api.add_resource(CourseResource, '/courses/<int:course_id>')
api.add_resource(CourseAssignmentsResource,
                 '/courses/<int:course_id>/assignments')

api.add_resource(AssignmentResource,
                 '/courses/<int:course_id>/assignments/<int:assignment_id>')

api.add_resource(AssignmentResourceCreator,
                 '/courses/<int:course_id>/assignments')

api.add_resource(SchoolResource, '/schools/<int:school_id>')

api.add_resource(ProjectResource, '/projects/<int:project_id>')
api.add_resource(UserProjectsResource, '/users/<user_id>/projects')

api.add_resource(UnitResource, '/courses/<int:course_id>/units/<int:unit_id>')
api.add_resource(UnitListResource, '/courses/<int:course_id>/units')

api.add_resource(FileResource, '/files/<int:file_id>')

api.add_resource(StatefulSet, '/deployments/<deployment_id>')

api.add_resource(QuickDeployResource, "/apps/quick-deploy/<int:course_id>/<int:assignment_id>")
api.add_resource(QuickFileSyncResource, "/apps/file-sync/<user_id>/")
