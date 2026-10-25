import os
import uuid
import numpy as np
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from dotenv import load_dotenv
from db import execute_query, execute_write
from common.period_tracker import (
    calculate_intervals,
    validate_cycle_inputs,
    recalculate_user_cycles,
    log_cycle,
    delete_user_cycle,
    update_cycle_clarification,
    calculate_period_prediction,
    calculate_cycle_analytics_metrics,
)
from common.wellbeing_tracker import get_user_wellbeing_insights
from common.doctor_summary import get_user_doctor_summary, render_doctor_summary_html

VALID_ENERGY_LEVELS = {"High", "Moderate", "Low", "Very Low"}

_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_ENV_FILE)

app = Flask(__name__)

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
auth_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="ovacare-auth-token-v1")
DEFAULT_TOKEN_MAX_AGE = int(os.getenv("AUTH_TOKEN_MAX_AGE", 86400 * 7)) # 7-day token validity

# Restrict CORS to specific frontend development origins
FRONTEND_ORIGINS = os.getenv(
    "CORS_ORIGINS", 
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"
).split(",")
allowed_origins = [o.strip() for o in FRONTEND_ORIGINS if o.strip()]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# ==========================================
# Authentication Helpers & Middleware
# ==========================================

def generate_auth_token(user_id):
    """Generates a cryptographically signed, timestamped auth token."""
    return auth_serializer.dumps({"user_id": user_id})

def verify_auth_token(token, max_age=None):
    """Verifies and decodes the auth token. Returns user_id or None."""
    if not token or not isinstance(token, str):
        return None
    if max_age is None:
        max_age = DEFAULT_TOKEN_MAX_AGE
    try:
        data = auth_serializer.loads(token, max_age=max_age)
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
        user_id = verify_auth_token(token)
        if not user_id:
            return jsonify({"error": "Unauthorized: Invalid or expired token"}), 401
            
        # Verify user still exists in database
        users = execute_query(
            "SELECT user_id, username, email, age, lifestyle, has_pcos, pcos_diagnosis_status, role FROM users WHERE user_id = :uid",
            {"uid": user_id}
        )
        if not users:
            return jsonify({"error": "Unauthorized: User account no longer exists"}), 401
            
        current_user = users[0]
        current_user['has_pcos'] = bool(current_user['has_pcos'])
        current_user['pcos_diagnosis_status'] = current_user.get('pcos_diagnosis_status') or 'prefer_not_to_say'
        current_user['role'] = current_user.get('role') or 'member'
        return f(current_user=current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    """
    Decorator to enforce administrator role authorization on endpoints.
    Enforces valid authentication and ensures the authenticated user has the 'admin' role.
    Returns 401 for missing/invalid/expired token, 403 for authenticated non-admin accounts.
    """
    @wraps(f)
    @token_required
    def decorated(current_user, *args, **kwargs):
        if current_user.get('role') != 'admin':
            return jsonify({"error": "Forbidden: Administrator privileges required"}), 403
        return f(current_user=current_user, *args, **kwargs)
    return decorated

# ==========================================
# Health Check Endpoint
# ==========================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "OvaCare backend is running"}), 200

# ==========================================
# 1. User Authentication Module
# ==========================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing required fields: username, email, and password"}), 400
        
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    raw_password = str(data.get('password', ''))
    
    if len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters"}), 400
        
    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email address format"}), 400
        
    if len(raw_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400
        
    # Hash password securely using Werkzeug PBKDF2:SHA256
    hashed_password = generate_password_hash(raw_password)
    
    age = data.get('age')
    if age is not None and age != "":
        try:
            age = int(age)
            if age < 10 or age > 120:
                return jsonify({"error": "Age must be between 10 and 120"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Age must be a valid number"}), 400
    else:
        age = None
        
    lifestyle = data.get('lifestyle', 'Moderate')
    if lifestyle not in ['Sedentary', 'Moderate', 'Active']:
        lifestyle = 'Moderate'
        
    has_pcos = bool(data.get('has_pcos', False))
    raw_diag = str(data.get('pcos_diagnosis_status', 'prefer_not_to_say')).strip().lower()
    valid_diag = {'diagnosed', 'suspected', 'prefer_not_to_say'}
    pcos_diagnosis_status = raw_diag if raw_diag in valid_diag else 'prefer_not_to_say'
    
    # Check if user already exists
    existing = execute_query("SELECT user_id FROM users WHERE email = :email", {"email": email})
    if existing:
        return jsonify({"error": "User with this email already exists"}), 400
        
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    try:
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos, pcos_diagnosis_status)
            VALUES (:user_id, :username, :email, :password, :age, :lifestyle, :has_pcos, :pcos_diagnosis_status)
            """,
            {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password": hashed_password,
                "age": age,
                "lifestyle": lifestyle,
                "has_pcos": has_pcos,
                "pcos_diagnosis_status": pcos_diagnosis_status
            }
        )
        token = generate_auth_token(user_id)
        return jsonify({
            "message": "User registered successfully",
            "token": token,
            "user": {
                "user_id": user_id,
                "username": username,
                "email": email,
                "age": age,
                "lifestyle": lifestyle,
                "has_pcos": has_pcos,
                "pcos_diagnosis_status": pcos_diagnosis_status,
                "role": "member"
            }
        }), 201
    except Exception as e:
        return jsonify({"error": "Database error during registration"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing email or password"}), 400
        
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    
    user = execute_query("SELECT * FROM users WHERE email = :email", {"email": email})
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401
        
    user_data = user[0]
    db_pass = user_data.get('password', '')
    
    # Securely reject legacy placeholder accounts with a clear message
    if "mockpbkdf2key" in db_pass:
        return jsonify({"error": "This legacy account cannot authenticate directly. Please use the Demo Mode or register a new account."}), 401
        
    # Verify using Werkzeug's check_password_hash
    try:
        is_valid = check_password_hash(db_pass, password)
    except Exception:
        is_valid = False
        
    if not is_valid:
        return jsonify({"error": "Invalid email or password"}), 401
        
    token = generate_auth_token(user_data['user_id'])
    is_demo_user = bool("demo" in str(user_data['email']).lower() or "demo" in str(user_data['username']).lower())
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "user_id": user_data['user_id'],
            "username": user_data['username'],
            "email": user_data['email'],
            "age": user_data['age'],
            "lifestyle": user_data['lifestyle'],
            "has_pcos": bool(user_data['has_pcos']),
            "pcos_diagnosis_status": user_data.get('pcos_diagnosis_status') or 'prefer_not_to_say',
            "role": user_data.get('role', 'member'),
            "is_demo": is_demo_user
        }
    }), 200

@app.route('/api/auth/demo', methods=['POST'])
def demo_login():
    """
    Safely authenticates a dedicated synthetic demo account.
    Prioritizes Maya Demo (maya.demo@example.com), optionally allows specifying
    a target demo email in the request JSON (e.g. jordan.gap@example.com),
    and falls back to legacy demo@ovacare.app if needed.
    """
    req_json = request.get_json(silent=True) or {}
    requested_email = req_json.get('email')

    user = None
    if requested_email and 'demo' in str(requested_email).lower():
        user = execute_query("SELECT * FROM users WHERE email = :email", {"email": str(requested_email).strip().lower()})

    if not user:
        # Prioritize primary Maya Demo account
        user = execute_query("SELECT * FROM users WHERE email = :email", {"email": "maya.demo@example.com"})

    if not user:
        # Fallback to legacy demo account
        user = execute_query("SELECT * FROM users WHERE email = :email", {"email": "demo@ovacare.app"})

    if not user:
        return jsonify({"error": "Demo account is not configured in the database"}), 500
        
    user_data = user[0]
    token = generate_auth_token(user_data['user_id'])
    return jsonify({
        "message": "Demo session initialized",
        "token": token,
        "user": {
            "user_id": user_data['user_id'],
            "username": user_data['username'],
            "email": user_data['email'],
            "age": user_data['age'],
            "lifestyle": user_data['lifestyle'],
            "has_pcos": bool(user_data['has_pcos']),
            "pcos_diagnosis_status": user_data.get('pcos_diagnosis_status') or 'prefer_not_to_say',
            "role": user_data.get('role', 'member'),
            "is_demo": True
        }
    }), 200

# ==========================================
# 2. User Profile Management Module (Task B)
# ==========================================

@app.route('/api/users/<user_id>', methods=['GET'])
@token_required
def get_user_profile(current_user, user_id):
    if current_user['user_id'] != user_id:
        return jsonify({"error": "Forbidden: Cannot view profile of another user"}), 403
    return jsonify({"user": current_user}), 200

@app.route('/api/users/<user_id>', methods=['PUT'])
@token_required
def update_profile(current_user, user_id):
    """
    Updates supported profile fields for the authenticated user only.
    Enforces ownership and validates input types and value bounds.
    """
    if current_user['user_id'] != user_id:
        return jsonify({"error": "Forbidden: Cannot update profile of another user"}), 403
        
    data = request.json
    if data is None or not isinstance(data, dict):
        return jsonify({"error": "Invalid request body"}), 400
        
    allowed_fields = {'age', 'lifestyle', 'has_pcos', 'pcos_diagnosis_status'}
    disallowed = set(data.keys()) - allowed_fields
    if disallowed:
        return jsonify({"error": f"Cannot modify restricted field(s): {', '.join(sorted(disallowed))}"}), 400
        
    updates = {}
    params = {"user_id": user_id}
    
    if 'age' in data:
        age_val = data.get('age')
        if age_val is not None and age_val != "":
            try:
                age_int = int(age_val)
                if age_int < 10 or age_int > 120:
                    return jsonify({"error": "Age must be between 10 and 120"}), 400
                updates['age'] = ":age"
                params['age'] = age_int
            except (ValueError, TypeError):
                return jsonify({"error": "Age must be a valid number"}), 400
        else:
            updates['age'] = ":age"
            params['age'] = None
            
    if 'lifestyle' in data:
        lifestyle_val = data.get('lifestyle')
        valid_lifestyles = ['Sedentary', 'Moderate', 'Active']
        if lifestyle_val not in valid_lifestyles:
            return jsonify({"error": f"Lifestyle must be one of: {', '.join(valid_lifestyles)}"}), 400
        updates['lifestyle'] = ":lifestyle"
        params['lifestyle'] = lifestyle_val
        
    if 'has_pcos' in data:
        has_pcos_val = data.get('has_pcos')
        if not isinstance(has_pcos_val, bool):
            return jsonify({"error": "has_pcos must be a boolean (true/false)"}), 400
        updates['has_pcos'] = ":has_pcos"
        params['has_pcos'] = has_pcos_val

    if 'pcos_diagnosis_status' in data:
        raw_status = data.get('pcos_diagnosis_status')
        valid_statuses = {'diagnosed', 'suspected', 'prefer_not_to_say'}
        if raw_status is None or str(raw_status).strip() == '':
            pcos_status = 'prefer_not_to_say'
        else:
            pcos_status = str(raw_status).strip().lower()
            if pcos_status not in valid_statuses:
                return jsonify({"error": f"pcos_diagnosis_status must be one of: {', '.join(sorted(valid_statuses))}"}), 400
        updates['pcos_diagnosis_status'] = ":pcos_diag_status"
        params['pcos_diag_status'] = pcos_status
        
    if not updates:
        return jsonify({"message": "No valid fields provided to update", "user": current_user}), 200
        
    set_clause = ", ".join([f"{col} = {val}" for col, val in updates.items()])
    sql = f"UPDATE users SET {set_clause} WHERE user_id = :user_id"
    
    try:
        execute_write(sql, params)
        updated = execute_query(
            "SELECT user_id, username, email, age, lifestyle, has_pcos, pcos_diagnosis_status, role FROM users WHERE user_id = :user_id",
            {"user_id": user_id}
        )[0]
        updated['has_pcos'] = bool(updated['has_pcos'])
        updated['pcos_diagnosis_status'] = updated.get('pcos_diagnosis_status') or 'prefer_not_to_say'
        updated['role'] = updated.get('role', 'member')
        return jsonify({"message": "Profile updated successfully", "user": updated}), 200
    except Exception as e:
        return jsonify({"error": "Database error while updating profile"}), 500

# ==========================================
# 3. Menstrual Cycle Tracking Module
# ==========================================

@app.route('/api/cycles', methods=['GET'])
@token_required
def get_cycles(current_user):
    user_id = current_user['user_id']
    cycles = execute_query(
        "SELECT * FROM cycles WHERE user_id = :user_id ORDER BY start_date DESC",
        {"user_id": user_id}
    )
    return jsonify(cycles), 200

@app.route('/api/cycles', methods=['POST'])
@token_required
def add_cycle(current_user):
    user_id = current_user['user_id']
    data = request.json
    if not data or not data.get('start_date'):
        return jsonify({"error": "Missing required field: start_date"}), 400
        
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    gap_clarification = data.get('gap_clarification')
    
    cycle_id, err, code = log_cycle(
        user_id=user_id,
        start_date_str=start_date_str,
        end_date_str=end_date_str,
        gap_clarification=gap_clarification
    )
    if err:
        return jsonify({"error": err}), code
        
    return jsonify({"message": "Cycle logged successfully", "cycle_id": cycle_id}), 201

@app.route('/api/cycles/<cycle_id>', methods=['DELETE'])
@token_required
def delete_cycle(current_user, cycle_id):
    user_id = current_user['user_id']
    success, message, code = delete_user_cycle(user_id, cycle_id)
    if not success:
        return jsonify({"error": message}), code
    return jsonify({"message": message}), code

@app.route('/api/cycles/<cycle_id>', methods=['PUT', 'PATCH'])
@app.route('/api/cycles/<cycle_id>/clarify', methods=['POST', 'PUT'])
@token_required
def clarify_cycle(current_user, cycle_id):
    user_id = current_user['user_id']
    data = request.json or {}
    gap_clarification = data.get('gap_clarification') or data.get('gap_type')
    if not gap_clarification:
        return jsonify({"error": "Missing required field: gap_clarification"}), 400
    success, message, code = update_cycle_clarification(user_id, cycle_id, gap_clarification)
    if not success:
        return jsonify({"error": message}), code
    return jsonify({"message": message}), code

# ==========================================
# 4. Mood & Symptom Tracking Module
# ==========================================

@app.route('/api/logs', methods=['GET'])
@token_required
def get_logs(current_user):
    user_id = current_user['user_id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = "SELECT * FROM wellness_logs WHERE user_id = :user_id"
    params = {"user_id": user_id}
    
    if start_date:
        query += " AND date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND date <= :end_date"
        params["end_date"] = end_date
        
    query += " ORDER BY date DESC"
    logs = execute_query(query, params)
    return jsonify(logs), 200

@app.route('/api/logs', methods=['POST'])
@token_required
def save_log(current_user):
    user_id = current_user['user_id']
    data = request.json
    if not data or not data.get('date'):
        return jsonify({"error": "Missing required field: date"}), 400
        
    date_str = data.get('date')
    try:
        log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400
    
    # Calculate cycle_day: get the most recent cycle start date before/on log_date
    curr_cycle = execute_query(
        """
        SELECT start_date FROM cycles 
        WHERE user_id = :user_id AND start_date <= :date 
        ORDER BY start_date DESC LIMIT 1
        """,
        {"user_id": user_id, "date": log_date}
    )
    
    cycle_day = None
    if curr_cycle:
        cycle_start = datetime.strptime(curr_cycle[0]['start_date'], "%Y-%m-%d").date()
        cycle_day = (log_date - cycle_start).days + 1
        
    # Validate optional energy_level when supplied
    energy_level = None
    if 'energy_level' in data:
        raw_energy = data.get('energy_level')
        if raw_energy is not None and str(raw_energy).strip() != '':
            e_str = str(raw_energy).strip()
            matched = None
            for valid in VALID_ENERGY_LEVELS:
                if e_str.lower() == valid.lower():
                    matched = valid
                    break
            if not matched:
                return jsonify({"error": "Invalid energy_level. Allowed values: High, Moderate, Low, Very Low"}), 400
            energy_level = matched
        else:
            energy_level = None

    # Handle optional notes
    notes = None
    if 'notes' in data:
        raw_notes = data.get('notes')
        if raw_notes is not None:
            notes = str(raw_notes).strip() if str(raw_notes).strip() else None

    # Check if a log exists for this date for this user
    existing = execute_query(
        "SELECT * FROM wellness_logs WHERE user_id = :user_id AND date = :date",
        {"user_id": user_id, "date": log_date}
    )
    
    try:
        if existing:
            prev = existing[0]
            log_id = prev['log_id']

            # Update only fields present in payload, preserving omitted fields
            updated_mood = data['mood'] if 'mood' in data else prev.get('mood')
            updated_stress = data['stress'] if 'stress' in data else prev.get('stress')
            updated_sleep = data['sleep_hours'] if 'sleep_hours' in data else prev.get('sleep_hours')
            updated_cramps = data['cramps'] if 'cramps' in data else prev.get('cramps')
            updated_fatigue = data['fatigue'] if 'fatigue' in data else prev.get('fatigue')
            updated_flow = data['flow'] if 'flow' in data else prev.get('flow')
            updated_energy = energy_level if 'energy_level' in data else prev.get('energy_level')
            updated_notes = notes if 'notes' in data else prev.get('notes')
            updated_cycle_day = cycle_day if cycle_day is not None else prev.get('cycle_day')

            execute_write(
                """
                UPDATE wellness_logs 
                SET cycle_day = :cycle_day, mood = :mood, stress = :stress, 
                    sleep_hours = :sleep_hours, cramps = :cramps, fatigue = :fatigue, flow = :flow,
                    energy_level = :energy_level, notes = :notes
                WHERE log_id = :log_id AND user_id = :user_id
                """,
                {
                    "cycle_day": updated_cycle_day,
                    "mood": updated_mood,
                    "stress": updated_stress,
                    "sleep_hours": updated_sleep,
                    "cramps": updated_cramps,
                    "fatigue": updated_fatigue,
                    "flow": updated_flow,
                    "energy_level": updated_energy,
                    "notes": updated_notes,
                    "log_id": log_id,
                    "user_id": user_id
                }
            )

            # Keep mood_logs consistent on update without duplicate records
            if 'mood' in data:
                if updated_mood:
                    existing_mood = execute_query(
                        "SELECT mood_log_id FROM mood_logs WHERE user_id = :user_id AND date = :date",
                        {"user_id": user_id, "date": log_date}
                    )
                    if existing_mood:
                        execute_write(
                            "UPDATE mood_logs SET mood = :mood WHERE user_id = :user_id AND date = :date",
                            {"mood": updated_mood, "user_id": user_id, "date": log_date}
                        )
                    else:
                        execute_write(
                            "INSERT INTO mood_logs (mood_log_id, user_id, mood, date) VALUES (:mood_log_id, :user_id, :mood, :date)",
                            {"mood_log_id": f"mld_{uuid.uuid4().hex[:12]}", "user_id": user_id, "mood": updated_mood, "date": log_date}
                        )
        else:
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            # For new records, omitted fields remain None/NULL, never coerced to 'None'
            new_mood = data.get('mood')
            new_stress = data.get('stress')
            new_sleep = data.get('sleep_hours')
            new_cramps = data.get('cramps')
            new_fatigue = data.get('fatigue')
            new_flow = data.get('flow')
            new_energy = energy_level
            new_notes = notes

            execute_write(
                """
                INSERT INTO wellness_logs (
                    log_id, user_id, date, cycle_day, mood, stress, sleep_hours,
                    cramps, fatigue, flow, energy_level, notes
                )
                VALUES (
                    :log_id, :user_id, :date, :cycle_day, :mood, :stress, :sleep_hours,
                    :cramps, :fatigue, :flow, :energy_level, :notes
                )
                """,
                {
                    "log_id": log_id,
                    "user_id": user_id,
                    "date": log_date,
                    "cycle_day": cycle_day,
                    "mood": new_mood,
                    "stress": new_stress,
                    "sleep_hours": new_sleep,
                    "cramps": new_cramps,
                    "fatigue": new_fatigue,
                    "flow": new_flow,
                    "energy_level": new_energy,
                    "notes": new_notes
                }
            )
            
            if new_mood:
                execute_write(
                    """
                    INSERT INTO mood_logs (mood_log_id, user_id, mood, date)
                    VALUES (:mood_log_id, :user_id, :mood, :date)
                    """,
                    {
                        "mood_log_id": f"mld_{uuid.uuid4().hex[:12]}",
                        "user_id": user_id,
                        "mood": new_mood,
                        "date": log_date
                    }
                )
            
        return jsonify({"message": "Wellness log saved successfully", "log_id": log_id, "cycle_day": cycle_day}), 200
    except Exception as e:
        return jsonify({"error": "Failed to save wellness log"}), 500

@app.route('/api/logs/<log_id>', methods=['DELETE'])
@token_required
def delete_log(current_user, log_id):
    user_id = current_user['user_id']
    try:
        log = execute_query(
            "SELECT user_id, date FROM wellness_logs WHERE log_id = :log_id",
            {"log_id": log_id}
        )
        if not log:
            return jsonify({"error": "Log not found"}), 404
        if log[0]['user_id'] != user_id:
            return jsonify({"error": "Unauthorized"}), 403

        execute_write(
            "DELETE FROM wellness_logs WHERE log_id = :log_id AND user_id = :user_id",
            {"log_id": log_id, "user_id": user_id}
        )
        execute_write(
            "DELETE FROM mood_logs WHERE user_id = :user_id AND date = :date",
            {"user_id": user_id, "date": log[0]['date']}
        )
        return jsonify({"message": "Wellness log deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete wellness log"}), 500

# ==========================================
# 5. Reminder Module
# ==========================================

@app.route('/api/reminders', methods=['GET'])
@token_required
def get_reminders(current_user):
    user_id = current_user['user_id']
    reminders = execute_query(
        "SELECT * FROM reminders WHERE user_id = :user_id ORDER BY reminder_date DESC",
        {"user_id": user_id}
    )
    return jsonify(reminders), 200

@app.route('/api/reminders', methods=['POST'])
@token_required
def add_reminder(current_user):
    user_id = current_user['user_id']
    data = request.json
    if not data or not data.get('reminder_type') or not data.get('reminder_date'):
        return jsonify({"error": "Missing required fields: reminder_type and reminder_date"}), 400
        
    reminder_id = f"rem_{uuid.uuid4().hex[:12]}"
    try:
        execute_write(
            """
            INSERT INTO reminders (reminder_id, user_id, reminder_type, reminder_date, completed)
            VALUES (:reminder_id, :user_id, :reminder_type, :reminder_date, :completed)
            """,
            {
                "reminder_id": reminder_id,
                "user_id": user_id,
                "reminder_type": data.get('reminder_type'),
                "reminder_date": data.get('reminder_date'),
                "completed": bool(data.get('completed', False))
            }
        )
        return jsonify({"message": "Reminder created successfully", "reminder_id": reminder_id}), 201
    except Exception as e:
        return jsonify({"error": "Failed to create reminder"}), 500

@app.route('/api/reminders/<reminder_id>/toggle', methods=['POST'])
@token_required
def toggle_reminder(current_user, reminder_id):
    user_id = current_user['user_id']
    try:
        reminder = execute_query(
            "SELECT user_id, completed FROM reminders WHERE reminder_id = :reminder_id", 
            {"reminder_id": reminder_id}
        )
        if not reminder:
            return jsonify({"error": "Reminder not found"}), 404
        if reminder[0]['user_id'] != user_id:
            return jsonify({"error": "Forbidden: Cannot modify reminders belonging to another user"}), 403
            
        new_val = not bool(reminder[0]['completed'])
        execute_write(
            "UPDATE reminders SET completed = :completed WHERE reminder_id = :reminder_id AND user_id = :user_id",
            {"completed": new_val, "reminder_id": reminder_id, "user_id": user_id}
        )
        return jsonify({"message": "Reminder updated successfully", "completed": new_val}), 200
    except Exception as e:
        return jsonify({"error": "Failed to toggle reminder"}), 500

@app.route('/api/reminders/<reminder_id>', methods=['DELETE'])
@token_required
def delete_reminder(current_user, reminder_id):
    user_id = current_user['user_id']
    try:
        reminder = execute_query(
            "SELECT user_id FROM reminders WHERE reminder_id = :reminder_id", 
            {"reminder_id": reminder_id}
        )
        if not reminder:
            return jsonify({"error": "Reminder not found"}), 404
        if reminder[0]['user_id'] != user_id:
            return jsonify({"error": "Forbidden: Cannot delete reminders belonging to another user"}), 403
            
        execute_write(
            "DELETE FROM reminders WHERE reminder_id = :reminder_id AND user_id = :user_id", 
            {"reminder_id": reminder_id, "user_id": user_id}
        )
        return jsonify({"message": "Reminder deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete reminder"}), 500

# ==========================================
# 6. Prediction System API
# ==========================================

@app.route('/api/predictions', methods=['GET'])
@token_required
def get_prediction(current_user):
    user_id = current_user['user_id']
    cycles = execute_query(
        """
        SELECT cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular, gap_type
        FROM cycles
        WHERE user_id = :user_id
        ORDER BY start_date DESC
        """,
        {"user_id": user_id}
    )
    has_pcos = bool(current_user.get('has_pcos', False))
    prediction_data = calculate_period_prediction(cycles, has_pcos=has_pcos)
    return jsonify(prediction_data), 200

# ==========================================
# 7. Analytics Module API
# ==========================================

@app.route('/api/analytics', methods=['GET'])
@token_required
def get_analytics(current_user):
    user_id = current_user['user_id']
    
    # 1. Cycle & Period History
    cycles_db = execute_query(
        """
        SELECT cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular, gap_type
        FROM cycles
        WHERE user_id = :user_id
        ORDER BY start_date ASC
        """,
        {"user_id": user_id}
    )
    
    # 2. Mood Frequency
    moods_db = execute_query(
        "SELECT mood, COUNT(*) as count FROM mood_logs WHERE user_id = :user_id GROUP BY mood ORDER BY count DESC",
        {"user_id": user_id}
    )
    
    # 3. Symptoms Frequency (Cramps & Fatigue from wellness_logs)
    cramps_db = execute_query(
        "SELECT cramps, COUNT(*) as count FROM wellness_logs WHERE user_id = :user_id AND cramps != 'None' GROUP BY cramps",
        {"user_id": user_id}
    )
    fatigue_db = execute_query(
        "SELECT fatigue, COUNT(*) as count FROM wellness_logs WHERE user_id = :user_id AND fatigue != 'None' GROUP BY fatigue",
        {"user_id": user_id}
    )
    
    # 4. Stress and Sleep Trends (last 30 logs)
    trends_db = execute_query(
        "SELECT date, sleep_hours, stress, mood, cycle_day FROM wellness_logs WHERE user_id = :user_id ORDER BY date DESC LIMIT 30",
        {"user_id": user_id}
    )
    trends_db.reverse()
    
    symptoms_freq = {
        "Cramps (Mild)": 0, "Cramps (Moderate)": 0, "Cramps (Severe)": 0,
        "Fatigue (Mild)": 0, "Fatigue (Moderate)": 0, "Fatigue (Severe)": 0
    }
                     
    for row in cramps_db:
        key = f"Cramps ({row['cramps']})"
        if key in symptoms_freq:
            symptoms_freq[key] = row['count']
            
    for row in fatigue_db:
        key = f"Fatigue ({row['fatigue']})"
        if key in symptoms_freq:
            symptoms_freq[key] = row['count']
            
    metrics = calculate_cycle_analytics_metrics(cycles_db)
    avg_cycle = metrics["average_cycle_length"]
    avg_period = metrics["average_period_length"]
    irregular_count = metrics["irregular_cycles_count"]
    
    insights = []
    if len(cycles_db) > 3:
        if irregular_count / len(cycles_db) > 0.4:
            insights.append("Your cycle logs indicate frequent irregularities. Track stress or consult an advisor.")
        else:
            insights.append("Your menstrual cycle remains mostly regular 💜")
            
    sleep_stress_db = execute_query(
        "SELECT stress, AVG(sleep_hours) as avg_sleep FROM wellness_logs WHERE user_id = :user_id GROUP BY stress",
        {"user_id": user_id}
    )
    
    for row in sleep_stress_db:
        if row['stress'] == 'High' and row['avg_sleep'] and row['avg_sleep'] < 6.5:
            insights.append(f"High stress is strongly linked to fewer sleep hours ({round(row['avg_sleep'], 1)} hrs average).")
            
    if not insights:
        insights.append("Logging daily helps build personalized wellness trends and emotional recommendations.")

    wellbeing_patterns_data = get_user_wellbeing_insights(user_id)

    return jsonify({
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "total_cycles_logged": len(cycles_db),
        "irregular_cycles_count": irregular_count,
        "cycle_history": cycles_db,
        "mood_frequencies": moods_db,
        "symptoms_frequencies": symptoms_freq,
        "recent_trends": trends_db,
        "insights": insights,
        "wellbeing_patterns": wellbeing_patterns_data
    }), 200

# ==========================================
# 7b. Unified My Health Report & Clinical Summary API
# ==========================================

@app.route('/api/reports/health-summary', methods=['GET'])
@app.route('/api/reports/doctor-summary', methods=['GET'])
@token_required
def get_health_report(current_user):
    """
    Generates the unified My Health Report strictly segregating:
    1. Recorded Facts (patient-confirmed cycle dates, bleeding lengths, flow logs)
    2. Statistical Estimates (average cycle length, prediction intervals, irregularity)
    3. User-Reported Symptoms (subjective comfort, sleep hours, mood, notes)
    Supports date range filtering via ?start_date=YYYY-MM-DD and ?end_date=YYYY-MM-DD.
    Supports ?format=json (default) and ?format=html (printable report).
    """
    user_id = current_user['user_id']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    fmt = request.args.get('format', 'json').lower()

    # Validate date formats if provided
    if start_date:
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid start_date format. Expected YYYY-MM-DD"}), 400

    if end_date:
        try:
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Expected YYYY-MM-DD"}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({"error": "start_date cannot be after end_date"}), 400

    try:
        summary_data = get_user_doctor_summary(user_id, start_date=start_date, end_date=end_date)
        if fmt in ('html', 'print'):
            html_content = render_doctor_summary_html(summary_data)
            return Response(html_content, mimetype='text/html; charset=utf-8')
        return jsonify(summary_data), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to generate health report"}), 500

# ==========================================
# 8. Admin Dashboard API (Secured & Anonymized)
# ==========================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats(current_user):
    """
    Returns aggregate research and platform metrics.
    Protected by admin authorization and anonymized: does NOT leak personal
    identifying details (emails, names, ages) or individual patient records.
    """
    total_users = execute_query("SELECT COUNT(*) as count FROM users")[0]['count']
    total_cycles = execute_query("SELECT COUNT(*) as count FROM cycles")[0]['count']
    total_logs = execute_query("SELECT COUNT(*) as count FROM wellness_logs")[0]['count']
    
    avg_cycle_len = execute_query("SELECT AVG(cycle_length) as avg FROM cycles")[0]['avg']
    avg_cycle_len = round(avg_cycle_len, 1) if avg_cycle_len else 28.0
    
    pcos_users = execute_query("SELECT COUNT(*) as count FROM users WHERE has_pcos = TRUE")[0]['count']
    pcos_ratio = round((pcos_users / total_users) * 100, 1) if total_users else 0.0
    
    # PCOS vs Cycle length aggregate analysis
    pcos_cycle_analysis = execute_query(
        """
        SELECT u.has_pcos, AVG(c.cycle_length) as avg_cycle, AVG(c.period_length) as avg_period, COUNT(c.cycle_id) as cycle_count
        FROM users u
        JOIN cycles c ON u.user_id = c.user_id
        GROUP BY u.has_pcos
        """
    )
    
    # Aggregate, de-identified activity cohorts (NO emails, names, or individual PHI)
    activity_cohorts = execute_query(
        """
        SELECT u.lifestyle, COUNT(DISTINCT u.user_id) as user_count, COUNT(l.log_id) as total_logs
        FROM users u
        LEFT JOIN wellness_logs l ON u.user_id = l.user_id
        GROUP BY u.lifestyle
        """
    )
    
    return jsonify({
        "total_users": total_users,
        "total_cycles": total_cycles,
        "total_logs": total_logs,
        "average_cycle_length": avg_cycle_len,
        "pcos_ratio_percentage": pcos_ratio,
        "pcos_cycle_analysis": pcos_cycle_analysis,
        "activity_cohorts": activity_cohorts
    }), 200

# ==========================================
# Community & Companion Blueprint Registrations
# ==========================================
from community import community_bp
app.register_blueprint(community_bp, url_prefix='/api/community')

from companion import companion_bp
app.register_blueprint(companion_bp, url_prefix='/api/companion')

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    default_debug = "True" if is_development_mode() else "False"
    host = os.getenv("HOST", "0.0.0.0")
    app.run(host=host, debug=debug_mode, port=port)
