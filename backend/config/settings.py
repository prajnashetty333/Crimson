import os
from dotenv import load_dotenv

# Path to .env file in the backend root directory
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_CONFIG_DIR, ".."))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")
load_dotenv(_ENV_FILE)

# Security & Secret Key Configuration
DEV_FALLBACK_SECRET = "ovacare-dev-secret-key-2026-safe-replace-in-prod"
INSECURE_SECRETS = {
    DEV_FALLBACK_SECRET.lower(),
    "replace-with-a-secure-random-secret-key-in-production",
    "secret",
    "changeme",
    "default",
}

def is_development_mode():
    """
    Returns True ONLY when the application is explicitly configured for local development
    via APP_ENV=development. Any other value — including an unset environment — returns False,
    ensuring production-grade secret enforcement is applied by default.
    """
    return os.getenv("APP_ENV", "").strip().lower() == "development"

def is_production_mode():
    """
    Returns True for any environment that is not explicitly set to local development.
    This is the fail-safe default: an unspecified environment is treated as production-like.
    """
    return not is_development_mode()

def load_secret_key():
    """
    Loads and validates the application SECRET_KEY.

    Development (APP_ENV=development):
      - Uses SECRET_KEY from environment if provided.
      - Allows the development-only fallback secret if SECRET_KEY is absent.

    Production / unspecified environment (anything other than APP_ENV=development):
      - Requires an environment-provided SECRET_KEY.
      - Rejects any known placeholder or predictable value.
      - Enforces a minimum length of 32 characters.
      - Fails startup immediately with a descriptive RuntimeError if any check fails.
      - The development fallback can NEVER be silently applied.
    """
    raw_secret = os.getenv("SECRET_KEY")
    secret = raw_secret.strip() if raw_secret else ""

    if is_development_mode():
        # Explicit local development: allow dev fallback when no key is provided
        return secret if secret else DEV_FALLBACK_SECRET

    # Production / unspecified — enforce strict requirements
    if not secret:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY environment variable is required. "
            "Set APP_ENV=development for local development, or provide a strong SECRET_KEY for production. "
            "Application startup aborted."
        )
    if secret.lower() in INSECURE_SECRETS or "replace-with" in secret.lower():
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: Predictable or placeholder SECRET_KEY detected. "
            "Application startup aborted. "
            "Generate a strong secret: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if len(secret) < 32:
        raise RuntimeError(
            f"CRITICAL SECURITY CONFIGURATION ERROR: SECRET_KEY is too weak ({len(secret)} chars). "
            "Production secrets must be at least 32 characters. "
            "Generate a strong secret: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret

SECRET_KEY = load_secret_key()
DEFAULT_TOKEN_MAX_AGE = int(os.getenv("AUTH_TOKEN_MAX_AGE", 86400 * 7))  # 7-day token validity

# Restrict CORS to specific frontend development origins
FRONTEND_ORIGINS = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
).split(",")
allowed_origins = [o.strip() for o in FRONTEND_ORIGINS if o.strip()]
