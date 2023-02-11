from flask_dance.consumer.storage.sqla import OAuthConsumerMixin

from ..connection import db


class OAuth(OAuthConsumerMixin, db.Model):  # type: ignore
    provider = db.Column(db.String(50))
    provider_email = db.Column(db.String, db.ForeignKey("users.email"))
    user = db.relationship("User")
