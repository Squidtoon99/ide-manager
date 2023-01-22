from ..connection import db
from .course_users import course_users


class Course(db.Model):  # type: ignore
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    join_code = db.Column(db.String(20), nullable=False, unique=True)

    users = db.relationship("User", secondary=course_users,
                         back_populates="courses", lazy="joined")

    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    school = db.relationship("School", back_populates="courses")
