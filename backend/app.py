import os
import uuid
import numpy as np
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from dotenv import load_dotenv
from db import execute_query, execute_write

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
            "SELECT user_id, username, email, age, lifestyle, has_pcos FROM users WHERE user_id = :uid", 
            {"uid": user_id}
        )
        if not users:
            return jsonify({"error": "Unauthorized: User account no longer exists"}), 401
            
        current_user = users[0]
        current_user['has_pcos'] = bool(current_user['has_pcos'])
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
    
    # Check if user already exists
    existing = execute_query("SELECT user_id FROM users WHERE email = :email", {"email": email})
    if existing:
        return jsonify({"error": "User with this email already exists"}), 400
        
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    try:
        execute_write(
            """
            INSERT INTO users (user_id, username, email, password, age, lifestyle, has_pcos)
            VALUES (:user_id, :username, :email, :password, :age, :lifestyle, :has_pcos)
            """,
            {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password": hashed_password,
                "age": age,
                "lifestyle": lifestyle,
                "has_pcos": has_pcos
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
                "has_pcos": has_pcos
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
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "user_id": user_data['user_id'],
            "username": user_data['username'],
            "email": user_data['email'],
            "age": user_data['age'],
            "lifestyle": user_data['lifestyle'],
            "has_pcos": bool(user_data['has_pcos'])
        }
    }), 200

@app.route('/api/auth/demo', methods=['POST'])
def demo_login():
    """
    Safely authenticates a dedicated synthetic demo account.
    Eliminates public admin endpoint reliance and arbitrary bypasses.
    """
    demo_email = "demo@ovacare.app"
    user = execute_query("SELECT * FROM users WHERE email = :email", {"email": demo_email})
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
            "has_pcos": bool(user_data['has_pcos'])
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
        
    allowed_fields = {'age', 'lifestyle', 'has_pcos'}
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
        
    if not updates:
        return jsonify({"message": "No valid fields provided to update", "user": current_user}), 200
        
    set_clause = ", ".join([f"{col} = {val}" for col, val in updates.items()])
    sql = f"UPDATE users SET {set_clause} WHERE user_id = :user_id"
    
    try:
        execute_write(sql, params)
        updated = execute_query(
            "SELECT user_id, username, email, age, lifestyle, has_pcos FROM users WHERE user_id = :user_id",
            {"user_id": user_id}
        )[0]
        updated['has_pcos'] = bool(updated['has_pcos'])
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
    
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
    except ValueError:
        return jsonify({"error": "Dates must be in YYYY-MM-DD format"}), 400
        
    if end_date and end_date < start_date:
        return jsonify({"error": "End date cannot be earlier than start date"}), 400
        
    period_length = (end_date - start_date).days if end_date else None
    cycle_id = f"cyc_{uuid.uuid4().hex[:12]}"
    
    # Get previous cycle to calculate cycle_length
    prev_cycle = execute_query(
        """
        SELECT * FROM cycles 
        WHERE user_id = :user_id AND start_date < :start_date 
        ORDER BY start_date DESC LIMIT 1
        """,
        {"user_id": user_id, "start_date": start_date}
    )
    
    cycle_length = None
    if prev_cycle:
        prev_start = datetime.strptime(prev_cycle[0]['start_date'], "%Y-%m-%d").date()
        cycle_length = (start_date - prev_start).days
        
    has_pcos = current_user['has_pcos']
    
    # Irregular calculation
    irregular = False
    if has_pcos:
        irregular = True
    elif cycle_length:
        avg_cycle_res = execute_query(
            "SELECT AVG(cycle_length) as avg_len FROM cycles WHERE user_id = :user_id", 
            {"user_id": user_id}
        )
        avg_len = avg_cycle_res[0]['avg_len'] if avg_cycle_res and avg_cycle_res[0]['avg_len'] else 28
        if abs(cycle_length - avg_len) > 4:
            irregular = True
            
    try:
        execute_write(
            """
            INSERT INTO cycles (cycle_id, user_id, start_date, end_date, cycle_length, period_length, irregular)
            VALUES (:cycle_id, :user_id, :start_date, :end_date, :cycle_length, :period_length, :irregular)
            """,
            {
                "cycle_id": cycle_id,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "cycle_length": cycle_length,
                "period_length": period_length,
                "irregular": irregular
            }
        )
        
        # Update previous cycle's cycle_length if a subsequent cycle was added
        next_cycle = execute_query(
            """
            SELECT * FROM cycles 
            WHERE user_id = :user_id AND start_date > :start_date 
            ORDER BY start_date ASC LIMIT 1
            """,
            {"user_id": user_id, "start_date": start_date}
        )
        if next_cycle:
            next_start = datetime.strptime(next_cycle[0]['start_date'], "%Y-%m-%d").date()
            new_prev_len = (next_start - start_date).days
            execute_write(
                "UPDATE cycles SET cycle_length = :cycle_length WHERE cycle_id = :cycle_id",
                {"cycle_length": new_prev_len, "cycle_id": cycle_id}
            )
            
        return jsonify({"message": "Cycle logged successfully", "cycle_id": cycle_id}), 201
    except Exception as e:
        return jsonify({"error": "Failed to log cycle record"}), 500

@app.route('/api/cycles/<cycle_id>', methods=['DELETE'])
@token_required
def delete_cycle(current_user, cycle_id):
    user_id = current_user['user_id']
    try:
        # Check ownership before deletion
        cycle = execute_query("SELECT user_id FROM cycles WHERE cycle_id = :cycle_id", {"cycle_id": cycle_id})
        if not cycle:
            return jsonify({"error": "Cycle not found"}), 404
        if cycle[0]['user_id'] != user_id:
            return jsonify({"error": "Forbidden: Cannot delete records belonging to another user"}), 403
            
        execute_write("DELETE FROM cycles WHERE cycle_id = :cycle_id AND user_id = :user_id", {"cycle_id": cycle_id, "user_id": user_id})
        return jsonify({"message": "Cycle deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to delete cycle record"}), 500

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
        
    mood = data.get('mood')
    stress = data.get('stress')
    sleep_hours = data.get('sleep_hours')
    cramps = data.get('cramps', 'None')
    fatigue = data.get('fatigue', 'None')
    flow = data.get('flow', 'None')
    
    # Check if a log exists for this date for this user
    existing = execute_query(
        "SELECT log_id FROM wellness_logs WHERE user_id = :user_id AND date = :date",
        {"user_id": user_id, "date": log_date}
    )
    
    try:
        if existing:
            log_id = existing[0]['log_id']
            execute_write(
                """
                UPDATE wellness_logs 
                SET cycle_day = :cycle_day, mood = :mood, stress = :stress, 
                    sleep_hours = :sleep_hours, cramps = :cramps, fatigue = :fatigue, flow = :flow
                WHERE log_id = :log_id AND user_id = :user_id
                """,
                {
                    "cycle_day": cycle_day,
                    "mood": mood,
                    "stress": stress,
                    "sleep_hours": sleep_hours,
                    "cramps": cramps,
                    "fatigue": fatigue,
                    "flow": flow,
                    "log_id": log_id,
                    "user_id": user_id
                }
            )
        else:
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            execute_write(
                """
                INSERT INTO wellness_logs (log_id, user_id, date, cycle_day, mood, stress, sleep_hours, cramps, fatigue, flow)
                VALUES (:log_id, :user_id, :date, :cycle_day, :mood, :stress, :sleep_hours, :cramps, :fatigue, :flow)
                """,
                {
                    "log_id": log_id,
                    "user_id": user_id,
                    "date": log_date,
                    "cycle_day": cycle_day,
                    "mood": mood,
                    "stress": stress,
                    "sleep_hours": sleep_hours,
                    "cramps": cramps,
                    "fatigue": fatigue,
                    "flow": flow
                }
            )
            
        if mood:
            execute_write(
                """
                INSERT INTO mood_logs (mood_log_id, user_id, mood, date)
                VALUES (:mood_log_id, :user_id, :mood, :date)
                """,
                {
                    "mood_log_id": f"mld_{uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "mood": mood,
                    "date": log_date
                }
            )
            
        return jsonify({"message": "Wellness log saved successfully", "log_id": log_id, "cycle_day": cycle_day}), 200
    except Exception as e:
        return jsonify({"error": "Failed to save wellness log"}), 500

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
        "SELECT start_date, cycle_length, period_length FROM cycles WHERE user_id = :user_id ORDER BY start_date DESC",
        {"user_id": user_id}
    )
    
    if not cycles:
        return jsonify({
            "predicted_date": (datetime.now() + timedelta(days=10)).date().isoformat(),
            "average_cycle_length": 28,
            "average_period_length": 5,
            "irregular": False,
            "history_count": 0,
            "delayed_days": 0,
            "message": "Not enough cycle history. Providing baseline prediction."
        }), 200
        
    cycle_lengths = [c['cycle_length'] for c in cycles if c['cycle_length'] is not None]
    period_lengths = [c['period_length'] for c in cycles if c['period_length'] is not None]
    
    avg_cycle = round(sum(cycle_lengths) / len(cycle_lengths)) if cycle_lengths else 28
    avg_period = round(sum(period_lengths) / len(period_lengths)) if period_lengths else 5
    
    last_start = datetime.strptime(cycles[0]['start_date'], "%Y-%m-%d").date()
    predicted_date = last_start + timedelta(days=avg_cycle)
    
    is_irregular = False
    if current_user['has_pcos']:
        is_irregular = True
    elif len(cycle_lengths) >= 3:
        std_dev = np.std(cycle_lengths)
        if std_dev > 4:
            is_irregular = True
            
    today = datetime.now().date()
    delayed_days = 0
    if today > predicted_date:
        delayed_days = (today - predicted_date).days
        
    return jsonify({
        "predicted_date": predicted_date.isoformat(),
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "irregular": is_irregular,
        "history_count": len(cycles),
        "delayed_days": delayed_days,
        "message": f"Your next period is predicted to start on {predicted_date.strftime('%B %d, %Y')}"
    }), 200

# ==========================================
# 7. Analytics Module API
# ==========================================

@app.route('/api/analytics', methods=['GET'])
@token_required
def get_analytics(current_user):
    user_id = current_user['user_id']
    
    # 1. Cycle & Period History
    cycles_db = execute_query(
        "SELECT start_date, cycle_length, period_length, irregular FROM cycles WHERE user_id = :user_id ORDER BY start_date ASC",
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
            
    cycle_lengths = [c['cycle_length'] for c in cycles_db if c['cycle_length'] is not None]
    period_lengths = [c['period_length'] for c in cycles_db if c['period_length'] is not None]
    
    avg_cycle = round(sum(cycle_lengths) / len(cycle_lengths), 1) if cycle_lengths else 28.0
    avg_period = round(sum(period_lengths) / len(period_lengths), 1) if period_lengths else 5.0
    irregular_count = sum(1 for c in cycles_db if c['irregular'])
    
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

    return jsonify({
        "average_cycle_length": avg_cycle,
        "average_period_length": avg_period,
        "total_cycles_logged": len(cycles_db),
        "irregular_cycles_count": irregular_count,
        "cycle_history": cycles_db,
        "mood_frequencies": moods_db,
        "symptoms_frequencies": symptoms_freq,
        "recent_trends": trends_db,
        "insights": insights
    }), 200

# ==========================================
# 8. Admin Dashboard API (Secured & Anonymized)
# ==========================================

@app.route('/api/admin/stats', methods=['GET'])
@token_required
def get_admin_stats(current_user):
    """
    Returns aggregate research and platform metrics.
    Protected by authentication and anonymized: does NOT leak personal
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

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    default_debug = "True" if is_development_mode() else "False"
    debug_mode = os.getenv("FLASK_DEBUG", default_debug).lower() == "true"
    app.run(debug=debug_mode, port=port)
