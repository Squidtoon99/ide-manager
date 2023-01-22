from .course_users import course_users
from ..connection import db


class User(db.Model):  # type: ignore
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image = db.Column(db.String(500), nullable=False)

    is_teacher = db.Column(db.Boolean, nullable=False)

    courses = db.relationship('Course', secondary=course_users,
                           back_populates="users", lazy="joined")

    school = db.relationship("School", back_populates="users", lazy="joined")
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    projects = db.relationship("Project", back_populates="user", lazy="joined")