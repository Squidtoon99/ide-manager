from flask_login import current_user
from werkzeug.exceptions import BadRequest

from ..connection import db


class Assignment(db.Model):  # type: ignore
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    is_published = db.Column(db.Boolean, nullable=False)

    projects = db.relationship('Project', back_populates="assignment")

    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    course = db.relationship('Course', back_populates="assignments")

    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'))
    unit = db.relationship('Unit', back_populates="assignments")

    @staticmethod
    def validate_data(data):
        if len(data.get("name", "")) == 0 or len(data.get("name", "")) > 100:
            raise BadRequest("Name must be between 1 and 100 characters")
        if len(data.get("description", "")) > 500:
            raise BadRequest("Description must be between 0 and 500 characters")
        if data.get("due_date") is None:
            raise BadRequest("Due date is required")
        if 'template' not in data:
            raise BadRequest("Template is required")
        template_name = data.get('template', {}).get('name') or ""

        if template_name.lower() not in ["java", "python"]:
            raise BadRequest("Template must be either 'java' or 'python'")
        return True

    @staticmethod
    def get_files(template):
        if template.get('name').lower() == 'java':
            return [
                {
                    "name": "Main.java",
                    "content": template.get('content')
                }
            ]
    @classmethod
    def initialize(cls, **data):
        cls.validate_data(data)

        # Create the assignment
        obj = cls(
            name=data.get("name"),
            description=data.get("description"),
            due_date=data.get("due_date"),
            is_published=False,
            course_id=data.get("course_id"),
            unit_id=data.get("unit_id"),
        )

        db.session.add(obj)
        db.session.commit()

        # get the id of the object
        data["assignment_id"] = obj.id

        # Create the blueprint from the template
        from db.models import Project

        blueprint = Project.create_blueprint(obj, current_user, obj.get_files(data['template']))


        db.session.add(blueprint)
        return obj
