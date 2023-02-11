from typing import TYPE_CHECKING

import requests
from flask_login import current_user

from . import File
from ..connection import db

if TYPE_CHECKING:
    from .assignment import Assignment
    from .user import User


# TODO: Add get method


class Project(db.Model):  # type: ignore
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    fs_path = db.Column(db.String(100), nullable=False)
    is_published = db.Column(db.Boolean, nullable=False)
    last_updated = db.Column(db.DateTime, nullable=True)

    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'))
    assignment = db.relationship("Assignment", back_populates="projects")

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User", back_populates="projects")

    files = db.relationship("File", back_populates="project")

    blueprint = db.Column(db.Boolean, nullable=False)

    def __repr__(self):
        return f"Project {self.name} {self.slug} {self.description} {self.due_date} {self.is_published}"

    @classmethod
    def create_blueprint(cls, assignment: "Assignment", user: "User") -> "Project":
        project = cls(
            fs_path=f"{assignment.name}-{assignment.id}",
            is_published=False,
            assignment=assignment,
            user=user,
            blueprint=True,
        )

        db.session.add(project)
        return project

    @classmethod
    def initialize(cls, assignment: "Assignment", user: "User") -> "Project":
        blueprint: Project = cls.query.filter_by(
            assignment_id=assignment.id, blueprint=True).first()
        if not blueprint:
            raise FileNotFoundError("No blueprint for this assignment")

        project = cls(
            fs_path=blueprint.fs_path,
            is_published=False,
            assignment=assignment,
            user=user,
            blueprint=False,
        )

        files = []
        for f in blueprint.files:
            files.append(project.create_file(f))

        db.session.add_all([project, *files])
        db.session.commit()
        return project

    def create_file(self, file: "File") -> "File":
        f = File(name=file.name, object=file.object, project=self)

        r = requests.post(
            f"http://vs-{current_user.id}-svc.default.svc.cluster.local:3000/save",
            json={
                "path": f"{self.fs_path}/{f.name}",
                "url": f"https://storage.googleapis.com/{f.object}"
            }
        )
        print(r.text, r.status_code)
        return f
