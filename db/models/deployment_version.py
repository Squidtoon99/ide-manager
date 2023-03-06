import base64
import hashlib
from datetime import datetime
from typing import TYPE_CHECKING

from ..connection import db

if TYPE_CHECKING:
    from typing import Self


class DeploymentVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    hash = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    
    @classmethod
    def get_latest(cls) -> "Self":
        return cls.query.order_by(cls.date.desc()).first()

    @classmethod
    def get_by_hash(cls, h: str) -> "Self":
        return cls.query.filter_by(hash=h).first()

    @staticmethod
    def hash_data(data: str) -> str:
        return base64.urlsafe_b64encode(hashlib.sha3_512(data.encode()).digest()).decode("utf8")
