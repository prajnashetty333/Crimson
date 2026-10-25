"""Authentication and authorization utilities for OvaCare AI backend."""
import os
import sys
from functools import wraps
from flask import request, jsonify
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Ensure backend root directory is on sys.path if imported in non-standard context
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_CURRENT_DIR, ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config.settings import SECRET_KEY, DEFAULT_TOKEN_MAX_AGE as _CONFIG_DEFAULT_TOKEN_MAX_AGE
from db import execute_query

# Module-level default token validity
DEFAULT_TOKEN_MAX_AGE = _CONFIG_DEFAULT_TOKEN_MAX_AGE

# Token serializer using configured SECRET_KEY and application salt
auth_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="ovacare-auth-token-v1")


def _resolve_auth_serializer():
    """
    Returns the active auth_serializer. If app.auth_serializer has been
    monkey-patched or overridden in tests, use that instead.
    """
    app_module = sys.modules.get("app")
    if app_module is not None and hasattr(app_module, "auth_serializer"):
        app_serializer = getattr(app_module, "auth_serializer")
        if app_serializer is not None:
            return app_serializer
    return auth_serializer


def _resolve_default_token_max_age():
    """
    Resolves DEFAULT_TOKEN_MAX_AGE dynamically.
    
    This preserves backward-compatible monkey-patching in existing tests,
    specifically `@patch('app.DEFAULT_TOKEN_MAX_AGE', -1)` in test_auth_security.py,
    while also supporting direct patching of `common.auth.DEFAULT_TOKEN_MAX_AGE`.
    """
    # 1. Check if common.auth.DEFAULT_TOKEN_MAX_AGE was explicitly modified
    if DEFAULT_TOKEN_MAX_AGE != _CONFIG_DEFAULT_TOKEN_MAX_AGE:
        return DEFAULT_TOKEN_MAX_AGE

    # 2. Check if app.DEFAULT_TOKEN_MAX_AGE was monkey-patched in tests
    app_module = sys.modules.get("app")
    if app_module is not None and hasattr(app_module, "DEFAULT_TOKEN_MAX_AGE"):
        return getattr(app_module, "DEFAULT_TOKEN_MAX_AGE")

    return DEFAULT_TOKEN_MAX_AGE


def generate_auth_token(user_id):
    """Generates a cryptographically signed, timestamped auth token."""
    serializer = _resolve_auth_serializer()
    return serializer.dumps({"user_id": user_id})


def verify_auth_token(token, max_age=None):
    """Verifies and decodes the auth token. Returns user_id or None."""
    if not token or not isinstance(token, str):
        return None
    if max_age is None:
        max_age = _resolve_default_token_max_age()
    try:
        serializer = _resolve_auth_serializer()
        data = serializer.loads(token, max_age=max_age)
        if isinstance(data, dict):
            return data.get("user_id")
        return None
    except (SignatureExpired, BadSignature, Exception):
        return None


def token_required(f):
    """
    Decorator to enforce authentication on protected endpoints.
    Extracts Bearer token, validates signature, ensures user exists in DB,
    and passes current_user to the decorated route handler.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Unauthorized: Authorization token required"}), 401
            
        token = auth_header.split(" ", 1)[1].strip()

        # Check if verify_auth_token has been patched on app
        app_module = sys.modules.get("app")
        if app_module is not None and hasattr(app_module, "verify_auth_token"):
            verify_func = getattr(app_module, "verify_auth_token")
        else:
            verify_func = verify_auth_token

        user_id = verify_func(token)
        if not user_id:
            return jsonify({"error": "Unauthorized: Invalid or expired token"}), 401
            
        # Verify user still exists in database
        users = execute_query(
            "SELECT user_id, username, email, age, lifestyle, has_pcos, pcos_diagnosis_status FROM users WHERE user_id = :uid",
            {"uid": user_id}
        )
        if not users:
            return jsonify({"error": "Unauthorized: User account no longer exists"}), 401
            
        current_user = users[0]
        current_user["has_pcos"] = bool(current_user["has_pcos"])
        current_user["pcos_diagnosis_status"] = current_user.get("pcos_diagnosis_status") or "prefer_not_to_say"
        return f(current_user=current_user, *args, **kwargs)
    return decorated
