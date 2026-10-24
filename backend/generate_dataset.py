import os
import random
import uuid
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from faker import Faker
from sqlalchemy import create_engine, MetaData, Table, Column, String, Integer, Float, Date, Boolean, ForeignKey, text
from dotenv import load_dotenv

load_dotenv()

fake = Faker('en_IN')
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Define Database connection
# Fallback to local SQLite if MySQL environment variables are not set
MYSQL_USER = os.getenv("MYSQL_USER", "")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_HOST = os.getenv("MYSQL_HOST", "")
MYSQL_DB = os.getenv("MYSQL_DATABASE", "")

if MYSQL_USER and MYSQL_PASSWORD and MYSQL_HOST and MYSQL_DB:
    DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    print(f"Connecting to MySQL Database at {MYSQL_HOST}...")
else:
    DATABASE_URL = "sqlite:///ovacare.db"
    print("No MySQL credentials found. Falling back to local SQLite database (ovacare.db)...")

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define tables using SQLAlchemy Core for compatibility between SQLite and MySQL
users = Table(
    'users', metadata,
    Column('user_id', String(50), primary_key=True),
    Column('username', String(100), nullable=False),
    Column('email', String(100), unique=True, nullable=False),
    Column('password', String(255), nullable=False),
    Column('age', Integer),
    Column('lifestyle', String(100)),
    Column('has_pcos', Boolean, default=False)
)

cycles = Table(
    'cycles', metadata,
    Column('cycle_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('start_date', Date, nullable=False),
    Column('end_date', Date),
    Column('cycle_length', Integer),
    Column('period_length', Integer),
    Column('irregular', Boolean, default=False)
)

wellness_logs = Table(
    'wellness_logs', metadata,
    Column('log_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('date', Date, nullable=False),
    Column('cycle_day', Integer),
    Column('mood', String(50)),
    Column('stress', String(50)),
    Column('sleep_hours', Float),
    Column('cramps', String(50)),
    Column('fatigue', String(50)),
    Column('flow', String(50))
)

mood_logs = Table(
    'mood_logs', metadata,
    Column('mood_log_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('mood', String(50), nullable=False),
    Column('date', Date, nullable=False)
)

reminders = Table(
    'reminders', metadata,
    Column('reminder_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('reminder_type', String(100), nullable=False),
    Column('reminder_date', Date, nullable=False),
    Column('completed', Boolean, default=False)
)

predictions = Table(
    'predictions', metadata,
    Column('prediction_id', String(50), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
    Column('predicted_date', Date, nullable=False),
    Column('actual_date', Date),
    Column('accuracy', Float)
)

# Clear and recreate tables to ensure stale Western names are removed
metadata.drop_all(engine)
metadata.create_all(engine)

# Data Generation Settings
NUM_USERS = 100
DAYS_OF_HISTORY = 730  # 2 years

print(f"Generating synthetic data for {NUM_USERS} users over {DAYS_OF_HISTORY} days...")

user_list = []
cycle_list = []
wellness_log_list = []
mood_log_list = []
reminder_list = []
prediction_list = []

lifestyles = ['Sedentary', 'Active', 'Moderate']
mood_options = ['Happy', 'Calm', 'Emotional', 'Irritated', 'Tired', 'Anxious']
stress_options = ['Low', 'Medium', 'High']
severity_options = ['None', 'Mild', 'Moderate', 'Severe']
flow_options = ['None', 'Light', 'Medium', 'Heavy']
reminder_types = ['Hydration', 'Medicine', 'Period', 'Self-Care']

start_date_range = datetime.now() - timedelta(days=DAYS_OF_HISTORY)

for i in range(NUM_USERS):
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    username = fake.name()
    email = fake.unique.email()
    password = "pbkdf2:sha256:260000$mockpbkdf2key"  # static hashed password mock
    age = random.randint(18, 45)
    lifestyle = random.choice(lifestyles)
    
    # 20% PCOS probability, which strongly correlates with irregular cycles
    has_pcos = random.random() < 0.20
    
    user_list.append({
        "user_id": user_id,
        "username": username,
        "email": email,
        "password": password,
        "age": age,
        "lifestyle": lifestyle,
        "has_pcos": has_pcos
    })
    
    # Establish cycle characteristics for this user
    if has_pcos:
        # Irregular cycle: average 35-50 days, high deviation
        mean_cycle = random.randint(35, 48)
        std_cycle = random.randint(5, 12)
        mean_period = random.randint(5, 9)
    else:
        # Regular cycle: average 26-32 days, low deviation
        mean_cycle = random.randint(26, 32)
        std_cycle = random.randint(1, 3)
        mean_period = random.randint(3, 7)
        
    current_date = start_date_range + timedelta(days=random.randint(0, 30))
    user_cycles = []
    
    # Track cycles
    while current_date < datetime.now():
        cycle_id = f"cyc_{uuid.uuid4().hex[:12]}"
        
        # Calculate actual lengths using normal distribution
        cycle_len = int(np.clip(np.random.normal(mean_cycle, std_cycle), 21, 60))
        period_len = int(np.clip(np.random.normal(mean_period, 1.2), 2, 12))
        
        # If cycle length deviates from user's mean by more than 4 days, mark as irregular
        is_irregular = abs(cycle_len - mean_cycle) > 4 or has_pcos
        
        start_date = current_date.date()
        end_date = (current_date + timedelta(days=period_len)).date()
        
        cycle_data = {
            "cycle_id": cycle_id,
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date,
            "cycle_length": cycle_len,
            "period_length": period_len,
            "irregular": bool(is_irregular)
        }
        user_cycles.append(cycle_data)
        cycle_list.append(cycle_data)
        
        # Predict next cycle date and record it
        predicted_date = (current_date + timedelta(days=cycle_len)).date()
        prediction_id = f"prd_{uuid.uuid4().hex[:12]}"
        
        # If the predicted date has already passed, we can populate the actual date
        actual_date = None
        accuracy = None
        
        next_cycle_start = current_date + timedelta(days=cycle_len)
        if next_cycle_start < datetime.now():
            actual_date = next_cycle_start.date()
            accuracy = float(max(0, 100 - abs(cycle_len - mean_cycle) * 5)) # Mocked accuracy metric
            
        prediction_list.append({
            "prediction_id": prediction_id,
            "user_id": user_id,
            "predicted_date": predicted_date,
            "actual_date": actual_date,
            "accuracy": accuracy
        })
        
        current_date = current_date + timedelta(days=cycle_len)
        
    # Generate daily wellness logs based on cycles
    if user_cycles:
        # Build lookup of period days
        period_dates = {}
        for cyc in user_cycles:
            s = datetime.combine(cyc["start_date"], datetime.min.time())
            for d in range(cyc["cycle_length"]):
                curr = s + timedelta(days=d)
                if curr >= datetime.now():
                    break
                # Cycle day is 1-indexed
                cycle_day = d + 1
                is_period = d < cyc["period_length"]
                period_dates[curr.date()] = (cycle_day, is_period)
                
        # Generate logs for every date in range that we projected
        history_start = datetime.combine(user_cycles[0]["start_date"], datetime.min.time())
        for d_idx in range((datetime.now() - history_start).days):
            log_date = (history_start + timedelta(days=d_idx)).date()
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            
            cycle_day = 1
            is_period = False
            if log_date in period_dates:
                cycle_day, is_period = period_dates[log_date]
            else:
                # If outside tracked cycles, just mock cycle day
                cycle_day = (d_idx % 28) + 1
                
            # Log characteristics depending on period day
            if is_period:
                # Heavy symptoms on day 1-2, lighter later
                if cycle_day <= 2:
                    cramps = random.choice(['Moderate', 'Severe'])
                    fatigue = random.choice(['Moderate', 'Severe'])
                    flow = random.choice(['Medium', 'Heavy'])
                    mood = random.choice(['Tired', 'Irritated', 'Emotional'])
                    stress = random.choice(['Medium', 'High'])
                else:
                    cramps = random.choice(['Mild', 'Moderate'])
                    fatigue = random.choice(['Mild', 'Moderate'])
                    flow = random.choice(['Light', 'Medium'])
                    mood = random.choice(['Tired', 'Calm', 'Emotional'])
                    stress = random.choice(['Low', 'Medium'])
            else:
                # Ovulation window (e.g. days 12-16)
                if 12 <= cycle_day <= 16:
                    cramps = 'None'
                    fatigue = 'None'
                    flow = 'None'
                    mood = random.choice(['Happy', 'Calm'])
                    stress = 'Low'
                else:
                    # Normal days
                    cramps = 'None' if random.random() > 0.1 else 'Mild'
                    fatigue = 'None' if random.random() > 0.15 else 'Mild'
                    flow = 'None'
                    mood = random.choice(mood_options)
                    stress = random.choice(stress_options)
                    
            sleep_hours = float(np.clip(np.random.normal(7.2, 1.0 if not is_period else 1.5), 4, 10))
            sleep_hours = round(sleep_hours, 1)
            
            # Wellness Log
            wellness_log_list.append({
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
            })
            
            # Separate mood log entry (say 30% of days have a specific emotional log)
            if random.random() < 0.3:
                mood_log_list.append({
                    "mood_log_id": f"mld_{uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "mood": mood,
                    "date": log_date
                })
                
            # Random Reminders (Hydration, medicine, etc.)
            if random.random() < 0.05:
                reminder_list.append({
                    "reminder_id": f"rem_{uuid.uuid4().hex[:12]}",
                    "user_id": user_id,
                    "reminder_type": random.choice(reminder_types),
                    "reminder_date": log_date,
                    "completed": random.random() < 0.85
                })

# Batch inserts
with engine.begin() as conn:
    print("Writing Users to database...")
    conn.execute(users.insert(), user_list)
    print("Writing Cycles to database...")
    conn.execute(cycles.insert(), cycle_list)
    print("Writing Wellness Logs (this may take a moment)...")
    # Insert in chunks of 5000 for efficiency
    for chunk in [wellness_log_list[x:x+5000] for x in range(0, len(wellness_log_list), 5000)]:
        conn.execute(wellness_logs.insert(), chunk)
    print("Writing Mood Logs...")
    for chunk in [mood_log_list[x:x+5000] for x in range(0, len(mood_log_list), 5000)]:
        conn.execute(mood_logs.insert(), chunk)
    print("Writing Reminders...")
    conn.execute(reminders.insert(), reminder_list)
    print("Writing Predictions...")
    conn.execute(predictions.insert(), prediction_list)

print("Dataset generation complete!")
print(f"Total Users inserted: {len(user_list)}")
print(f"Total Cycles inserted: {len(cycle_list)}")
print(f"Total Wellness Logs inserted: {len(wellness_log_list)}")
print(f"Total Mood Logs inserted: {len(mood_log_list)}")
print(f"Total Reminders inserted: {len(reminder_list)}")
print(f"Total Predictions inserted: {len(prediction_list)}")
