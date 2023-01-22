from ..connection import db

# project files
class File(db.Model): # type: ignore
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    bucket = db.Column(db.String(255), nullable=False)
    
    project = db.relationship("Project", back_populates="files")
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))