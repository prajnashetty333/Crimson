# OvaCare Mini Project — Product Requirements Document (PRD)

# 1. Project Title

## OvaCare
### Smart Menstrual Wellness Tracking and Prediction System

---

# 2. Project Overview

OvaCare is a smart menstrual wellness tracking and management system designed to help users monitor menstrual cycles, symptoms, moods, wellness patterns, and basic health insights.

Unlike traditional calendar-based period trackers, OvaCare focuses on behavioral wellness tracking and intelligent data analysis using structured menstrual health data.

The mini project focuses on:

- Database management
- Menstrual wellness tracking
- Synthetic healthcare data handling
- Dashboard analytics
- Basic prediction system
- User-friendly wellness experience

The project is designed as a scalable foundation for a future AI-powered healthcare platform.

---

# 3. Problem Statement

Most existing menstrual tracking systems:

- only track period dates,
- provide generic predictions,
- require excessive manual input,
- do not support irregular cycle analysis,
- lack emotional wellness tracking,
- fail to provide personalized wellness insights.

Additionally, many systems lack proper data organization and analytical capabilities for long-term wellness monitoring.

OvaCare aims to solve these limitations by providing a structured menstrual wellness database system with analytics and intelligent tracking features.

---

# 4. Objectives

The primary objectives of OvaCare are:

- To design a structured menstrual wellness database system.
- To track menstrual cycles and wellness patterns.
- To manage symptom and mood records efficiently.
- To generate analytics and wellness insights.
- To provide basic cycle prediction.
- To support irregular cycle tracking.
- To demonstrate scalable healthcare database architecture.

---

# 5. Scope of the Mini Project

The mini project includes:

## Included Features

- User authentication
- Cycle tracking
- Symptom tracking
- Mood tracking
- Wellness dashboard
- Reminder system
- Basic prediction logic
- Analytics module
- Synthetic dataset integration
- Admin dashboard

## Excluded Features (Future Scope)

- Full AI prediction engine
- LSTM integration
- Wearable device integration
- Real-time medical diagnosis
- Hormonal analysis
- PCOS prediction AI
- Voice assistant
- Large-scale cloud deployment

---

# 6. Target Users

The application is intended for:

- Students
- Young adults
- Women tracking menstrual wellness
- Users with irregular cycles
- Healthcare research demonstrations

---

# 7. Functional Requirements

# 7.1 User Authentication Module

## Features

- User registration
- Login/logout
- Password protection
- User profile management

## Inputs

- Username
- Email
- Password
- Age
- Lifestyle information

## Outputs

- Secure user account
- Personalized dashboard

---

# 7.2 Menstrual Cycle Tracking Module

## Features

- Add cycle start date
- Add cycle end date
- Calculate cycle length
- Track period duration
- Detect irregular cycles

## Inputs

- Start date
- End date
- Flow intensity

## Outputs

- Cycle history
- Cycle statistics
- Calendar visualization

---

# 7.3 Symptom Tracking Module

## Features

Track symptoms such as:

- cramps
- headache
- fatigue
- acne
- bloating
- nausea
- back pain

## Inputs

- Symptom type
- Severity level
- Date

## Outputs

- Symptom history
- Symptom frequency analysis

---

# 7.4 Mood Tracking Module

## Features

Track emotional wellness:

- happy
- anxious
- emotional
- irritated
- tired
- calm

## Inputs

- Mood type
- Mood intensity
- Date

## Outputs

- Mood trends
- Emotional wellness analytics

---

# 7.5 Wellness Dashboard

## Features

- Cycle calendar
- Graphs and charts
- Symptom trends
- Mood analytics
- Wellness summaries

## Outputs

- User wellness overview
- Monthly statistics

---

# 7.6 Reminder Module

## Features

- Period reminders
- Hydration reminders
- Medicine reminders
- Wellness reminders

## Outputs

- Notification alerts
- Reminder completion tracking

---

# 7.7 Basic Prediction System

## Features

- Next period date prediction
- Average cycle estimation
- Delay warning

## Prediction Logic

The system predicts the next cycle using average cycle length:

next_period_date = last_period_date + average_cycle_length

## Outputs

- Predicted period date
- Cycle regularity information

---

# 7.8 Analytics Module

## Features

- Average cycle length
- Most common symptoms
- Mood frequency analysis
- Stress pattern analysis
- Irregular cycle reports

## Outputs

- Statistical charts
- Monthly reports
- Wellness trends

---

# 7.9 Admin Dashboard

## Features

- User management
- Dataset monitoring
- Analytics overview
- Report generation

---

# 8. Non-Functional Requirements

## Performance

- Fast data retrieval
- Responsive dashboard
- Efficient database queries

## Security

- Password encryption
- Secure authentication
- Protected user records

## Reliability

- Consistent data storage
- Accurate analytics
- Stable system performance

## Scalability

- Support future AI integration
- Expandable database structure

## Usability

- Simple interface
- Minimal user input
- Easy navigation

---

# 9. System Architecture

## Step 1

User enters wellness data

↓

## Step 2

Data stored in database

↓

## Step 3

Analytics engine processes data

↓

## Step 4

Prediction system calculates next cycle

↓

## Step 5

Dashboard displays insights

---

# 10. Database Design

# Main Tables

## 10.1 Users Table

| Field | Type |
|---|---|
| user_id | VARCHAR |
| username | VARCHAR |
| email | VARCHAR |
| password | VARCHAR |
| age | INT |
| lifestyle | VARCHAR |
| has_pcos | BOOLEAN |

---

## 10.2 Cycles Table

| Field | Type |
|---|---|
| cycle_id | VARCHAR |
| user_id | VARCHAR |
| start_date | DATE |
| end_date | DATE |
| cycle_length | INT |
| period_length | INT |
| irregular | BOOLEAN |

---

## 10.3 Wellness Logs Table

| Field | Type |
|---|---|
| log_id | VARCHAR |
| user_id | VARCHAR |
| date | DATE |
| cycle_day | INT |
| mood | VARCHAR |
| stress | VARCHAR |
| sleep_hours | FLOAT |
| cramps | VARCHAR |
| fatigue | VARCHAR |
| flow | VARCHAR |

---

## 10.4 Symptoms Table

| Field | Type |
|---|---|
| symptom_id | VARCHAR |
| symptom_name | VARCHAR |

---

## 10.5 Mood Logs Table

| Field | Type |
|---|---|
| mood_log_id | VARCHAR |
| user_id | VARCHAR |
| mood | VARCHAR |
| date | DATE |

---

## 10.6 Reminders Table

| Field | Type |
|---|---|
| reminder_id | VARCHAR |
| user_id | VARCHAR |
| reminder_type | VARCHAR |
| reminder_date | DATE |
| completed | BOOLEAN |

---

## 10.7 Predictions Table

| Field | Type |
|---|---|
| prediction_id | VARCHAR |
| user_id | VARCHAR |
| predicted_date | DATE |
| actual_date | DATE |
| accuracy | FLOAT |

---

# 11. Synthetic Dataset Design

The project uses synthetic healthcare data generated using Python.

## Dataset Characteristics

- 100–300 users
- 1000+ cycle records
- 20,000+ wellness logs
- Realistic irregularities
- Mood variations
- Symptom trends
- Stress patterns

## Tools for Dataset Generation

- Python
- Pandas
- Faker
- NumPy

---

# 12. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React / Flutter |
| Backend | Flask / Node.js |
| Database | MySQL / PostgreSQL |
| Charts | Chart.js |
| Authentication | Firebase Auth |
| Dataset Generation | Python |
| Hosting | Render / Vercel |

---

# 13. User Interface Modules

## Screens

- Login Screen
- Registration Screen
- Dashboard Screen
- Cycle Tracking Screen
- Symptom Logging Screen
- Mood Tracking Screen
- Analytics Screen
- Reminder Screen
- Admin Dashboard

---

# 14. Sample SQL Queries

## Query 1

Users with irregular cycles:

SELECT * FROM cycles WHERE irregular = TRUE;

---

## Query 2

Average cycle length:

SELECT AVG(cycle_length) FROM cycles;

---

## Query 3

Most common symptom:

SELECT symptom_name, COUNT(*)
FROM symptoms
GROUP BY symptom_name;

---

## Query 4

Users with severe cramps:

SELECT * FROM wellness_logs
WHERE cramps = 'severe';

---

# 15. Expected Outcomes

The project is expected to:

- Demonstrate healthcare database management.
- Provide menstrual wellness tracking.
- Generate wellness analytics.
- Support basic prediction functionality.
- Simulate a scalable AI-ready healthcare platform.

---

# 16. Future Enhancements

Future versions of OvaCare may include:

- LSTM-based AI prediction
- Adaptive learning system
- Mood prediction AI
- Wearable device integration
- Voice health logging
- Emotional wellness assistant
- PCOS risk analysis
- Offline AI prediction

---

# 17. Advantages of OvaCare

- Structured healthcare database system
- User-friendly wellness tracking
- Realistic synthetic healthcare dataset
- Analytics-driven design
- Expandable AI-ready architecture
- Personalized wellness monitoring

---

# 18. Conclusion

OvaCare is a smart menstrual wellness tracking and prediction system designed to improve menstrual health management through structured data handling, wellness tracking, analytics, and prediction.

The project demonstrates database management concepts, healthcare analytics, and scalable system design while laying the foundation for future AI-powered menstrual wellness intelligence systems.

