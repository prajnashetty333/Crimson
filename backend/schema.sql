-- OvaCare Database Schema for MySQL

CREATE DATABASE IF NOT EXISTS ovacare_db;
USE ovacare_db;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    age INT,
    lifestyle VARCHAR(100), -- E.g., 'Sedentary', 'Active', 'Moderate'
    has_pcos BOOLEAN DEFAULT FALSE,
    pcos_diagnosis_status VARCHAR(50) DEFAULT 'prefer_not_to_say',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Cycles Table
CREATE TABLE IF NOT EXISTS cycles (
    cycle_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    cycle_length INT, -- calculated dynamically: diff between consecutive cycle starts
    period_length INT, -- calculated: start_date to end_date
    irregular BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 3. Wellness Logs Table
CREATE TABLE IF NOT EXISTS wellness_logs (
    log_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    cycle_day INT, -- calculated cycle day count from start_date
    mood VARCHAR(50), -- E.g., 'Happy', 'Calm', 'Emotional', 'Irritated', 'Tired', 'Anxious'
    stress VARCHAR(50), -- E.g., 'Low', 'Medium', 'High'
    sleep_hours FLOAT,
    cramps VARCHAR(50), -- E.g., 'None', 'Mild', 'Moderate', 'Severe'
    fatigue VARCHAR(50), -- E.g., 'None', 'Mild', 'Moderate', 'Severe'
    flow VARCHAR(50), -- E.g., 'None', 'Light', 'Medium', 'Heavy'
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE KEY uniq_user_date (user_id, date)
);

-- 4. Symptoms Lookup Table
CREATE TABLE IF NOT EXISTS symptoms (
    symptom_id VARCHAR(50) PRIMARY KEY,
    symptom_name VARCHAR(100) UNIQUE NOT NULL
);

-- Seed Symptoms
INSERT IGNORE INTO symptoms (symptom_id, symptom_name) VALUES
('sym_1', 'Cramps'),
('sym_2', 'Headache'),
('sym_3', 'Fatigue'),
('sym_4', 'Acne'),
('sym_5', 'Bloating'),
('sym_6', 'Nausea'),
('sym_7', 'Back Pain');

-- 5. Mood Logs Table (for detailed mood logging trends)
CREATE TABLE IF NOT EXISTS mood_logs (
    mood_log_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    mood VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 6. Reminders Table
CREATE TABLE IF NOT EXISTS reminders (
    reminder_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    reminder_type VARCHAR(100) NOT NULL, -- 'Hydration', 'Medicine', 'Period', 'Self-Care'
    reminder_date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 7. Predictions Table
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    predicted_date DATE NOT NULL,
    actual_date DATE DEFAULT NULL,
    accuracy FLOAT DEFAULT NULL, -- percentage accuracy or deviation in days
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);
