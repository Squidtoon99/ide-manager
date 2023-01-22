from functools import wraps
from flask import redirect, url_for, jsonify
from flask_dance.contrib.google import google
from functools import lru_cache


@lru_cache(maxsize=100)
def _user(_cache_key):
    data = google.get("/oauth2/v2/userinfo")  # type: ignore
    # assertion to break cache with invalid data
    assert data.ok, data.text
    return data.json()


def require_auth(f):
    @wraps(f)
    def decorator(*args, **kw):
        try:
            assert google.authorized and google.token   # type: ignore
            resp = _user(google.token['access_token'])  # type: ignore
        except AssertionError:
            return jsonify({"error": "not authorized"}), 401
        return f(resp, *args, **kw)
    return decorator
