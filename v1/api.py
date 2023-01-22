from db.models import User, School, Course, Assignment, Project, File
from db.schemas import user_schema, school_schema, course_schema, assignment_schema, project_schema, file_schema
from db.connection import db
from flask import Blueprint, jsonify, request
import re
from typing import Union, Literal
from flask_login import login_required
from flask_restful import Resource, Api
# from .decorators import require_auth

api = Api(prefix="/api/v1/", decorators=[login_required])

bp = Blueprint('v1', __name__, url_prefix='/api/v1',
               template_folder='templates')

VALID_NAME = re.compile(r'^[a-zA-Z0-9_]+$')
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


class UserResource(Resource):
    def get(self, user_id):
        user = User.query.get_or_404(user_id)
        return user_schema.dump(user)

    def delete(self, user_id):
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return user_schema.dump(user)


class SchoolResource(Resource):
    def get(self, school_id):
        school = School.query.get_or_404(school_id)
        return school_schema.dump(school)


class AssignmentResource(Resource):
    def get(self, assignment_id):
        assignment = Assignment.query.get_or_404(assignment_id)
        return assignment_schema.dump(assignment)


class ProjectResource(Resource):
    def get(self, project_id):
        project = Project.query.get_or_404(project_id)
        return project_schema.dump(project)


class FileResource(Resource):
    def get(self, file_id):
        file = File.query.get_or_404(file_id)
        return file_schema.dump(file)


api.add_resource(UserResource, '/users/<int:user_id>')

api.add_resource(SchoolResource, '/schools/<int:school_id>')

api.add_resource(AssignmentResource, '/assignments/<int:assignment_id>')

api.add_resource(ProjectResource, '/projects/<int>')

api.add_resource(FileResource, '/files/<int:file_id>')