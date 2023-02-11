from ..connection import db

course_users = db.Table("course_users", db.Column(
    "course_id", db.Integer, db.ForeignKey("courses.id"), primary_key=True),
                        db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True)
                        )
