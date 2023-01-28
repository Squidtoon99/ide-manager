from flask_dance.consumer.storage.sqla import OAuthConsumerMixin

from ..connection import db


class OAuth(OAuthConsumerMixin, db.Model):  # type: ignore
    pass
