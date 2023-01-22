from ..connection import db


class Assignment(db.Model):  # type: ignore
    __tablename__ = 'assignments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    is_published = db.Column(db.Boolean, nullable=False)

    projects = db.relationship('Project', back_populates="assignment")
