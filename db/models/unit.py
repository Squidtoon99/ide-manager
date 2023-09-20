from ..connection import db


class Unit(db.Model):  # type: ignore
    __tablename__ = 'units'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    course = db.relationship('Course', back_populates='units')

    assignments = db.relationship('Assignment', back_populates='unit', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Unit {self.name}>'
