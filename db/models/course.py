from .course_users import course_users
from ..connection import db


class Course(db.Model):  # type: ignore
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    join_code = db.Column(db.String(20), nullable=False, unique=True)

    users = db.relationship("User", secondary=course_users,
                            back_populates="courses", lazy="joined")

    featured_teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    featured_teacher = db.relationship("User", back_populates="featured_courses")

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    school = db.relationship("School", back_populates="courses")

    assignments = db.relationship("Assignment", back_populates="course")

    units = db.relationship("Unit", back_populates="course")
