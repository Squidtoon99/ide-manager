from ..connection import db

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

    def __repr__(self):
        return f"Project {self.name} {self.slug} {self.description} {self.due_date} {self.is_published}"