from ..connection import db


# project files
class File(db.Model):  # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    object = db.Column(db.String(255), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship("User", back_populates="files")

    project = db.relationship("Project", back_populates="files")
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))

    sync = db.Column(db.Boolean, nullable=False, default=False)