# OvaCare — Implementation Plan & Todo List

This document outlines the systematic implementation phases and tasks to build **OvaCare**, a Smart Menstrual Wellness Tracking and Prediction System, matching the product requirements (PRD) and UI/UX design specifications.

---

## 🚀 Architecture & Tech Stack
- **Frontend**: React (Vite) + Tailwind CSS + Chart.js + Lucide Icons
- **Backend**: Flask + MySQL Connector / SQLAlchemy
- **Database**: MySQL (relational database tracking cycles, logs, mood, and symptoms)
- **Data Seeding**: Python script using Pandas, Faker, and NumPy to generate synthetic patient data
- **Aesthetics**: Wellness-focused, soft UI, glassmorphism, and lavender/purple tones

---

## 🗓️ Implementation Phases & Tasks

### Phase 1: Project Setup & Structure
- [x] **1.1 Directory Initialization**
  - Create `/frontend` and `/backend` directories in the workspace.
- [x] **1.2 Backend Environment Setup**
  - Initialize python virtual environment (`venv`) inside `/backend`.
  - Install dependencies: `flask`, `flask-cors`, `mysql-connector-python`, `sqlalchemy`, `pandas`, `faker`, `numpy`, `python-dotenv`.
- [x] **1.3 Frontend Project Setup**
  - Initialize Vite React project: `npm create vite@latest frontend -- --template react`.
  - Install frontend dependencies: `tailwindcss`, `postcss`, `autoprefixer`, `lucide-react`, `chart.js`, `react-chartjs-2`, `react-router-dom`.
  - Configure Tailwind CSS with the design document's palette:
    - Primary Purple: `#8B5CF6`
    - Soft Lavender: `#C4B5FD`
    - Light Pink: `#FBCFE8`
    - Calm Background: `#F5F3FF`
    - Wellness White: `#FAFAFA`
  - Import google font **Poppins** as the primary font family.

---

### Phase 2: Database Schema & Synthetic Data Seeding
- [x] **2.1 Database Schema Definition**
  - Write SQL script `schema.sql` implementing the 7 core tables:
    - `users` (user metadata, age, lifestyle, pcos status)
    - `cycles` (cycle start/end, calculated cycle/period lengths, irregularity flag)
    - `wellness_logs` (daily logs capturing flow, mood, stress, sleep, cramps, fatigue)
    - `symptoms` (lookup metadata for symptoms like cramps, headache, fatigue, etc.)
    - `mood_logs` (separate logs for mood tracking trends)
    - `reminders` (reminders for hydration, medicine, periods, etc.)
    - `predictions` (predicted period dates vs actual dates and tracking accuracy)
- [x] **2.2 Synthetic Dataset Generator (`generate_dataset.py`)**
  - Write Python script to generate realistic synthetic history for 100–300 users.
  - Generate 1,000+ cycle records with realistic irregular variance.
  - Generate 20,000+ wellness logs aligned with cycle phases (e.g., severe cramps and fatigue on cycle days 1-3, higher stress correlation, irregular cycles).
  - Seed generated data directly into the SQLite/MySQL database.

---

### Phase 3: Flask Backend API Development
- [x] **3.1 Database Connection Service**
  - Set up a clean connection pool/manager using SQLAlchemy or raw MySQL connections in `db.py`.
- [x] **3.2 Authentication API**
  - Implement mock/Firebase-compatible user registration and login endpoints.
- [x] **3.3 Cycle Tracking API**
  - Create endpoints to fetch user cycle history, add a cycle (start/end date), and delete cycle logs.
  - Implement cycle length and period length calculation.
- [x] **3.4 Mood & Symptom Logs API**
  - Endpoints to fetch and save daily wellness logs (mood emojis, pain severity, sleep hours, stress).
- [x] **3.5 Analytics & Prediction API**
  - Implement prediction engine: calculate average cycle length, predict next cycle start date:
    `next_period_date = last_period_date + average_cycle_length`
  - Generate analytics summaries: most common symptoms, mood frequencies, cycle regularity reports, stress pattern analysis.
- [x] **3.6 Reminders & Profile API**
  - CRUD for user reminders and updating user lifestyle/profile preferences.
- [x] **3.7 Admin Dashboard API**
  - Endpoints for aggregate statistics: total users, total logged cycles, average cycle length, PCOS ratio.

---

### Phase 4: Frontend Development & UI Design
- [x] **4.1 Navigation & Layout Framework**
  - Build responsive layout with a floating bottom navigation bar for mobile/desktop.
  - Integrate soft glassmorphic style using Tailwind utilities (`backdrop-blur-md`, `bg-white/70`, soft box-shadows).
- [x] **4.2 User Authentication Screens**
  - Create elegant login & sign-up forms with welcoming wellness copy.
- [x] **4.3 Main Dashboard Screen**
  - Welcome banner with emotional/care messages: `"Your body may need extra care today 💜"`.
  - Core Period Status Widget (cycle day, prediction, days remaining).
  - Quick Logging modal/section for mood selection and symptom severity sliders.
- [x] **4.4 Cycle Tracking & Calendar Screen**
  - Interactive calendar displaying menstrual history, predicted dates, and fertile window highlights.
- [x] **4.5 Mood & Symptom Wellness Screen**
  - Pill-shaped symptom chips, custom emoji sliders for mood, and fatigue logs.
- [x] **4.6 Analytics & Reports Screen**
  - Visual charts showing cycle trends, mood frequency, sleep vs stress patterns, and symptom distributions using Chart.js.
  - Insights cards with encouraging wellness recommendations.
- [x] **4.7 Reminder & Profile Settings Screen**
  - Form/toggles to configure and activate reminders (hydration, self-care, pills).
  - Profile setting fields including PIN security toggle, lifestyle settings, and dark mode toggles.
- [x] **4.8 Admin Dashboard Screen**
  - Dedicated view displaying aggregate metrics tables, database status, and user lists.

---

### Phase 5: Integration, Testing & Refinement
- [x] **5.1 Frontend-Backend Integration**
  - Configure Axios/Fetch API calls linking the React client to Flask server endpoints.
- [x] **5.2 User Flow Verification**
  - Perform end-to-end testing of logging a new cycle, adding wellness logs, verifying database persistence, and seeing predicted dates adjust.
- [x] **5.3 Responsive & Aesthetic Polish**
  - Ensure compatibility across desktop, tablet, and mobile browsers.
  - Add micro-animations (scale effects on clicks, hover floating shadows, fade-in transitions).
