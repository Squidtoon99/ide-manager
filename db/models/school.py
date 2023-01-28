from ..connection import db


class School(db.Model):  # type: ignore
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    courses = db.relationship('Course', back_populates="school")
    users = db.relationship("User", back_populates="school")
    
    units = db.relationship('Unit', back_populates='school')