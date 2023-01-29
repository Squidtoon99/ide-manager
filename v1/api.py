import re
from typing import Union, Literal

from flask import Blueprint, jsonify, request
from flask_login import current_user
from flask_login import login_required
from flask_restful import Resource, Api

from db.connection import db
from db.models import User, School, Course, Assignment, Project, File
from db.schemas import user_schema, school_schema, course_schema, assignment_schema, project_schema, file_schema

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


def get():
    return user_schema.dump(current_user)


class SelfResource(Resource):
    pass


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


class CourseAssignmentsResource(Resource):
    @staticmethod
    def get(course_id: int):
        assignments = Assignment.query.filter_by(course_id=course_id).all()
        return assignment_schema.dump(assignments, many=True)


class ProjectResource(Resource):
    @staticmethod
    def get(project_id):
        project = Project.query.get_or_404(project_id)
        return project_schema.dump(project)


class FileResource(Resource):
    @staticmethod
    def get(file_id):
        file = File.query.get_or_404(file_id)
        return file_schema.dump(file)


api.add_resource(UserResource, '/users/<int:user_id>')
api.add_resource(SelfResource, '/users/@me')

api.add_resource(CourseResource, '/courses/<int:course_id>')
api.add_resource(CourseAssignmentsResource,
                 '/courses/<int:course_id>/assignments')

api.add_resource(AssignmentResource,
                 '/courses/<int:course_id>/assignments/<int:assignment_id>')

api.add_resource(SchoolResource, '/schools/<int:school_id>')

api.add_resource(ProjectResource, '/projects/<int:project_id>')

api.add_resource(FileResource, '/files/<int:file_id>')
