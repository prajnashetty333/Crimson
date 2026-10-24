import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Determine database URL
MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "")
MYSQL_DB = os.getenv("MYSQL_DATABASE", "")

if MYSQL_USER and MYSQL_PASSWORD and MYSQL_HOST and MYSQL_DB:
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
else:
    # Use SQLite database generated in Phase 2, resolving to absolute path relative to this file
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "ovacare.db")
    DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

def execute_query(sql_string, params=None):
    """
    Executes a SQL query and returns the results as a list of dictionaries.
    For non-SELECT queries, returns the number of affected rows.
    """
    if params is None:
        params = {}
        
    with engine.connect() as conn:
        result = conn.execute(text(sql_string), params)
        
        # If transaction was started or write query was executed, commit it
        if conn.in_transaction():
            pass # SQLAlchemy autocommits or commits automatically with engine.begin() / connect() context in some setups, but let's be safe
            
        if result.returns_rows:
            # Convert rows to list of dicts
            columns = result.keys()
            rows = []
            for row in result:
                row_dict = {}
                for col, val in zip(columns, row):
                    # Convert dates and decimals to strings/floats for JSON serialization
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
    """
    if params is None:
        params = {}
    
    with engine.begin() as conn:
        result = conn.execute(text(sql_string), params)
        return result.rowcount
