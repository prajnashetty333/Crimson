import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROTECTED_PROD_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "ovacare.db"))
DEFAULT_TEST_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "ovacare_test.db"))
DEFAULT_DEMO_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "ovacare_demo.db"))


def is_test_mode():
    """
    Returns True when automated testing is explicitly activated via
    OVACARE_TEST_MODE or an explicit test database environment variable.
    """
    val = os.getenv("OVACARE_TEST_MODE", "").strip().lower()
    return val in ("true", "1", "yes") or bool(os.getenv("TEST_DATABASE_PATH") or os.getenv("OVACARE_TEST_DB"))


def is_demo_mode():
    """
    Returns True when demo mode is explicitly activated via
    OVACARE_DEMO_MODE or an explicit demo database environment variable.
    """
    val = os.getenv("OVACARE_DEMO_MODE", "").strip().lower()
    return val in ("true", "1", "yes") or bool(os.getenv("DEMO_DATABASE_PATH") or os.getenv("OVACARE_DEMO_DB"))


def resolve_database_url():
    """
    Resolves the active database URL.
    In test mode: uses an isolated test SQLite database, strictly verifying it is NOT
    the protected production database.
    In demo mode: uses an isolated demo SQLite database, strictly verifying it is NOT
    the protected production database.
    In development/production mode: preserves MySQL configuration if provided,
    otherwise falls back to backend/ovacare.db.
    """
    if is_test_mode():
        test_path = os.getenv("TEST_DATABASE_PATH") or os.getenv("OVACARE_TEST_DB")
        if not test_path:
            test_path = DEFAULT_TEST_DB_PATH
        else:
            test_path = os.path.abspath(test_path)

        if os.path.abspath(test_path) == PROTECTED_PROD_DB_PATH:
            raise RuntimeError(
                f"CRITICAL DATABASE SAFETY VIOLATION: Test database path cannot be the "
                f"protected production database: {PROTECTED_PROD_DB_PATH}"
            )
        return f"sqlite:///{test_path}"

    if is_demo_mode():
        demo_path = os.getenv("DEMO_DATABASE_PATH") or os.getenv("OVACARE_DEMO_DB")
        if not demo_path:
            demo_path = DEFAULT_DEMO_DB_PATH
        else:
            demo_path = os.path.abspath(demo_path)

        if os.path.abspath(demo_path) == PROTECTED_PROD_DB_PATH:
            raise RuntimeError(
                f"CRITICAL DATABASE SAFETY VIOLATION: Demo database path cannot be the "
                f"protected production database: {PROTECTED_PROD_DB_PATH}"
            )
        return f"sqlite:///{demo_path}"

    MYSQL_USER = os.getenv("MYSQL_USER", "")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.getenv("MYSQL_HOST", "")
    MYSQL_DB = os.getenv("MYSQL_DATABASE", "")

    if MYSQL_USER and MYSQL_PASSWORD and MYSQL_HOST and MYSQL_DB:
        return f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    else:
        return f"sqlite:///{PROTECTED_PROD_DB_PATH}"


DATABASE_URL = resolve_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)


def get_active_db_path():
    """Returns the absolute path to the active SQLite database, or None if MySQL."""
    if DATABASE_URL.startswith("sqlite:///"):
        return os.path.abspath(DATABASE_URL.replace("sqlite:///", ""))
    return None


def is_active_db_protected():
    """Returns True if the currently connected database is the protected production database."""
    active = get_active_db_path()
    return bool(active and active == PROTECTED_PROD_DB_PATH)


def init_test_database(test_db_path=None, init_schema=True):
    """
    Safely switches the database engine to an isolated SQLite test database.
    Ensures the target is NOT the protected production database, initializes
    the test schema, and updates module-level engine and DATABASE_URL.
    """
    global engine, DATABASE_URL

    target = test_db_path or os.getenv("TEST_DATABASE_PATH") or os.getenv("OVACARE_TEST_DB") or DEFAULT_TEST_DB_PATH
    target_abs = os.path.abspath(target)

    if target_abs == PROTECTED_PROD_DB_PATH:
        raise RuntimeError(
            f"CRITICAL DATABASE SAFETY VIOLATION: Test database path cannot be the "
            f"protected production database: {PROTECTED_PROD_DB_PATH}"
        )

    os.environ["OVACARE_TEST_MODE"] = "true"
    os.environ["TEST_DATABASE_PATH"] = target_abs
    DATABASE_URL = f"sqlite:///{target_abs}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    if init_schema:
        _init_test_schema(engine)

    return target_abs


def init_demo_database(demo_db_path=None, init_schema=True):
    """
    Safely switches the database engine to an isolated SQLite demo database.
    Ensures the target is NOT the protected production database, initializes
    the demo schema, and updates module-level engine and DATABASE_URL.
    """
    global engine, DATABASE_URL

    target = demo_db_path or os.getenv("DEMO_DATABASE_PATH") or os.getenv("OVACARE_DEMO_DB") or DEFAULT_DEMO_DB_PATH
    target_abs = os.path.abspath(target)

    if target_abs == PROTECTED_PROD_DB_PATH:
        raise RuntimeError(
            f"CRITICAL DATABASE SAFETY VIOLATION: Demo database path cannot be the "
            f"protected production database: {PROTECTED_PROD_DB_PATH}"
        )

    os.environ["OVACARE_DEMO_MODE"] = "true"
    os.environ["DEMO_DATABASE_PATH"] = target_abs
    DATABASE_URL = f"sqlite:///{target_abs}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

    if init_schema:
        _init_test_schema(engine)

    return target_abs


def _init_test_schema(target_engine):
    """Initializes standard application tables and lookup seeds in the test database."""
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(50) PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        age INT,
        lifestyle VARCHAR(100),
        has_pcos BOOLEAN DEFAULT FALSE,
        pcos_diagnosis_status VARCHAR(50) DEFAULT 'prefer_not_to_say',
        role VARCHAR(50) DEFAULT 'member',
        is_community_banned BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS cycles (
        cycle_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE,
        cycle_length INT,
        period_length INT,
        irregular BOOLEAN DEFAULT FALSE,
        gap_type VARCHAR(50) DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS wellness_logs (
        log_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        date DATE NOT NULL,
        cycle_day INT,
        mood VARCHAR(50),
        stress VARCHAR(50),
        sleep_hours FLOAT,
        cramps VARCHAR(50),
        fatigue VARCHAR(50),
        flow VARCHAR(50),
        energy_level VARCHAR(50),
        notes TEXT,
        cycle_phase VARCHAR(50),
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE (user_id, date)
    );

    CREATE TABLE IF NOT EXISTS mood_logs (
        mood_log_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        mood VARCHAR(50) NOT NULL,
        date DATE NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS reminders (
        reminder_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        reminder_type VARCHAR(100) NOT NULL,
        reminder_date DATE NOT NULL,
        completed BOOLEAN DEFAULT FALSE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        predicted_date DATE NOT NULL,
        actual_date DATE DEFAULT NULL,
        accuracy FLOAT DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS symptoms (
        symptom_id VARCHAR(50) PRIMARY KEY,
        symptom_name VARCHAR(100) UNIQUE NOT NULL
    );

    INSERT OR IGNORE INTO symptoms (symptom_id, symptom_name) VALUES
    ('sym_1', 'Cramps'),
    ('sym_2', 'Headache'),
    ('sym_3', 'Fatigue'),
    ('sym_4', 'Acne'),
    ('sym_5', 'Bloating'),
    ('sym_6', 'Nausea'),
    ('sym_7', 'Back Pain');

    CREATE TABLE IF NOT EXISTS community_profiles (
        profile_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) UNIQUE NOT NULL,
        display_name VARCHAR(100) NOT NULL,
        avatar_key VARCHAR(50) NOT NULL DEFAULT 'avatar_lavender',
        bio VARCHAR(300) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS community_categories (
        category_id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        slug VARCHAR(100) UNIQUE NOT NULL,
        description VARCHAR(255),
        icon VARCHAR(50) DEFAULT 'Sparkles',
        display_order INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    INSERT OR IGNORE INTO community_categories (category_id, name, slug, description, icon, display_order) VALUES
    ('cat_pcos_symptoms', 'PCOS and Symptoms', 'pcos-symptoms', 'Discuss symptoms, hormonal fluctuations, cycle tracking, and lived experiences.', 'Heart', 1),
    ('cat_nutrition_lifestyle', 'Nutrition and Lifestyle', 'nutrition-lifestyle', 'Anti-inflammatory diets, balanced meals, supplements, and lifestyle habits.', 'Apple', 2),
    ('cat_mental_wellbeing', 'Mental Well-being', 'mental-wellbeing', 'A compassionate safe haven for mood support, anxiety, and emotional wellness.', 'Smile', 3),
    ('cat_exercise_sleep', 'Exercise, Sleep and Energy', 'exercise-sleep-energy', 'Low-impact workouts, restorative sleep practices, and combating chronic fatigue.', 'Moon', 4),
    ('cat_treatments', 'Treatment Experiences', 'treatment-experiences', 'Navigating doctor visits, therapies, medications, and holistic care pathways.', 'Activity', 5),
    ('cat_general', 'General Safe Space', 'general-safe-space', 'Community chit-chat, personal wins, words of encouragement, and mutual support.', 'Sparkles', 6);

    CREATE TABLE IF NOT EXISTS community_posts (
        post_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        category_id VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        body TEXT NOT NULL,
        is_anonymous BOOLEAN DEFAULT FALSE,
        health_label VARCHAR(50) NOT NULL DEFAULT 'Personal Experience',
        is_verified BOOLEAN DEFAULT FALSE,
        verified_by VARCHAR(50) NULL,
        verified_at TIMESTAMP NULL,
        verification_source_url VARCHAR(500) NULL,
        verification_notes TEXT NULL,
        status VARCHAR(20) DEFAULT 'active',
        is_locked BOOLEAN DEFAULT FALSE,
        view_count INT DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES community_categories(category_id) ON DELETE RESTRICT,
        FOREIGN KEY (verified_by) REFERENCES users(user_id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS community_comments (
        comment_id VARCHAR(50) PRIMARY KEY,
        post_id VARCHAR(50) NOT NULL,
        user_id VARCHAR(50) NOT NULL,
        parent_comment_id VARCHAR(50) NULL,
        body TEXT NOT NULL,
        is_anonymous BOOLEAN DEFAULT FALSE,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (parent_comment_id) REFERENCES community_comments(comment_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS community_reactions (
        reaction_id VARCHAR(50) PRIMARY KEY,
        post_id VARCHAR(50) NOT NULL,
        user_id VARCHAR(50) NOT NULL,
        reaction_type VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES community_posts(post_id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        UNIQUE (post_id, user_id, reaction_type)
    );

    CREATE TABLE IF NOT EXISTS community_reports (
        report_id VARCHAR(50) PRIMARY KEY,
        reporter_user_id VARCHAR(50) NOT NULL,
        content_type VARCHAR(20) NOT NULL,
        content_id VARCHAR(50) NOT NULL,
        reason VARCHAR(100) NOT NULL,
        explanation TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        reviewed_by VARCHAR(50) NULL,
        reviewed_at TIMESTAMP NULL,
        resolution_notes TEXT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (reporter_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL,
        UNIQUE (reporter_user_id, content_type, content_id)
    );

    CREATE TABLE IF NOT EXISTS community_blocks (
        block_id VARCHAR(50) PRIMARY KEY,
        blocker_user_id VARCHAR(50) NOT NULL,
        blocked_user_id VARCHAR(50) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (blocker_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (blocked_user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS community_moderation_logs (
        log_id VARCHAR(50) PRIMARY KEY,
        moderator_user_id VARCHAR(50) NOT NULL,
        action VARCHAR(50) NOT NULL,
        target_type VARCHAR(30) NOT NULL,
        target_id VARCHAR(50) NOT NULL,
        reason TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (moderator_user_id) REFERENCES users(user_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS community_user_restrictions (
        restriction_id VARCHAR(50) PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        restricted_by VARCHAR(50) NOT NULL,
        restriction_type VARCHAR(30) NOT NULL,
        expires_at TIMESTAMP NULL,
        reason TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
        FOREIGN KEY (restricted_by) REFERENCES users(user_id) ON DELETE CASCADE
    );
    """
    raw_conn = target_engine.raw_connection()
    try:
        raw_conn.executescript(ddl)
        cursor = raw_conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        cols = [r[1] for r in cursor.fetchall()]
        if "role" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'member'")
        if "is_community_banned" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN is_community_banned BOOLEAN DEFAULT 0")
        if "pcos_diagnosis_status" not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN pcos_diagnosis_status VARCHAR(50) DEFAULT 'prefer_not_to_say'")
        raw_conn.commit()
    finally:
        raw_conn.close()


def execute_query(sql_string, params=None):
    """
    Executes a SQL query and returns the results as a list of dictionaries.
    For non-SELECT queries, returns the number of affected rows.
    """
    if params is None:
        params = {}

    with engine.connect() as conn:
        result = conn.execute(text(sql_string), params)

        if result.returns_rows:
            columns = result.keys()
            rows = []
            for row in result:
                row_dict = {}
                for col, val in zip(columns, row):
                    if hasattr(val, 'isoformat'):
                        row_dict[col] = val.isoformat()
                    elif isinstance(val, (int, float, str, bool)) or val is None:
                        row_dict[col] = val
                    else:
                        row_dict[col] = str(val)
                rows.append(row_dict)
            return rows
        else:
            return result.rowcount


def execute_write(sql_string, params=None):
    """
    Executes a write query (INSERT, UPDATE, DELETE) inside a transaction and commits.
    Enforces a strict safety guard: blocks any write to the protected production database
    whenever test mode or demo mode is active.
    """
    if (is_test_mode() or is_demo_mode()) and is_active_db_protected():
        raise RuntimeError(
            f"CRITICAL DATABASE SAFETY VIOLATION: Attempted to execute write query on "
            f"protected production database ({PROTECTED_PROD_DB_PATH}) during isolated test/demo mode!"
        )

    if params is None:
        params = {}

    with engine.begin() as conn:
        result = conn.execute(text(sql_string), params)
        return result.rowcount
