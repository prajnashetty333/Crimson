"""Configuration module for OvaCare AI backend."""
from .settings import (
    _ENV_FILE,
    DEV_FALLBACK_SECRET,
    INSECURE_SECRETS,
    is_development_mode,
    is_production_mode,
    load_secret_key,
    SECRET_KEY,
    DEFAULT_TOKEN_MAX_AGE,
    FRONTEND_ORIGINS,
    allowed_origins,
)

__all__ = [
    "_ENV_FILE",
    "DEV_FALLBACK_SECRET",
    "INSECURE_SECRETS",
    "is_development_mode",
    "is_production_mode",
    "load_secret_key",
    "SECRET_KEY",
    "DEFAULT_TOKEN_MAX_AGE",
    "FRONTEND_ORIGINS",
    "allowed_origins",
]
