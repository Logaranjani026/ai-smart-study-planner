# AI-Based Smart Study Planner

A modern, full-stack, AI-powered college study planning platform built with **HTML5, CSS3, Tailwind CSS, JavaScript, Chart.js, Python Flask, and MySQL**.

---

## Core Features & Pages

### 9 Responsive Web Pages
1. **Landing Page (`/`)**: Hero showcase (*"Study Smarter, Not Harder."*), navigation bar, feature highlights, interactive AI timetable preview, Login/Register/Get Started CTAs.
2. **Student Registration & Login (`/login`, `/register`, `/forgot-password`)**: Secure registration with name, email, password (PBKDF2-SHA256 hashing), department, year of study, forgot/reset password flow, and sample student quick-fill.
3. **Student Dashboard (`/dashboard`)**: KPI cards (total subjects, study hours, completed/pending topics), daily progress bar & today's blocks, Chart.js weekly activity chart, upcoming exam countdowns, and personalized AI suggestions.
4. **Subject Management (`/subjects`)**: Add/edit/delete subjects, chapters, topics, priorities (`High`/`Medium`/`Low`), difficulty ratings (`1-5`), target weekly hours, and exam dates.
5. **AI Study Planner (`/planner`)**: Configure weekday/weekend hours, preferred study time, block duration, and prioritization strategy (`Balanced`, `Exam Crunch`, `Weak Topics First`), view daily & 7-day weekly grids, built-in Pomodoro focus timer, and 1-click **Adaptive Rescheduling**.
6. **Weak Topic Detection (`/weak-topics`)**: Rate topic understanding (`1-5`), log external quiz scores or take a **Quick Diagnostic Quiz**, inspect Weak/Average/Strong classification, and schedule spaced revisions.
7. **AI Study Assistant (`/assistant`)**: Context-aware chatbot grounded in your live subjects, weak topics, upcoming exams, and schedules to explain topics, suggest revisions, and optimize timetables.
8. **Progress Tracking (`/progress`)**: Daily/weekly hours, completed chapters & topics, subject-wise progress charts, study streak counter, and 14-day consistency heatmap.
9. **Reminder System (`/reminders`)**: Auto-synced upcoming exam alerts, daily study goal reminders, pending high-priority topic nudges, spaced revision alerts, and custom reminders.

### 5 Intelligent AI Modules (`ai_engine/`)
1. **Smart Timetable Generator** (`timetable_generator.py`): Weighted priority scheduling factoring exam proximity, difficulty, priority, and topic weakness.
2. **Weak Topic Detector** (`weak_topic_detector.py`): Composite weakness scoring (`0-100`) combining self-ratings, quiz scores, difficulty, and decay since last studied.
3. **Adaptive Study Planner** (`timetable_generator.py`): Preserves completed blocks and dynamically redistributes missed/unfinished sessions into upcoming days.
4. **Smart Revision Predictor** (`revision_predictor.py`): Spaced-repetition interval predictor pulled forward ahead of approaching exam dates.
5. **AI Study Assistant** (`study_assistant.py`): Concept explainer + personalized schedule and weak-topic mentor.

---

## Project Folder Structure

```text
smart study planner/
├── app.py                          # Flask app factory & HTTP server entrypoint
├── config.py                       # MySQL / SQLAlchemy / session configuration
├── requirements.txt                # Python package dependencies
├── pytest.ini                      # Pytest path configuration
├── .env.example                    # Environment configuration template
├── README.md                       # Setup, architecture & run guide
├── ai_engine/
│   ├── __init__.py
│   ├── timetable_generator.py      # Smart Timetable Generator + Adaptive Planner
│   ├── weak_topic_detector.py      # Weak Topic Detector & quiz/rating scorer
│   ├── revision_predictor.py       # Smart Revision Predictor (spaced repetition)
│   └── study_assistant.py          # Context-aware AI Study Assistant
├── database/
│   ├── schema.sql                  # Full MySQL 8.0 DDL (all 8 tables + FKs)
│   ├── seed_data.sql               # Sample college student SQL dataset
│   └── init_db.py                  # Automated MySQL DB + table + seed initializer
├── models/
│   ├── __init__.py
│   └── models.py                   # SQLAlchemy ORM models for all 8 MySQL tables
├── routes/
│   ├── __init__.py
│   ├── auth.py                     # Register, Login, Logout, Password Reset APIs
│   ├── pages.py                    # Page routes for all 9 views
│   └── api.py                      # REST APIs for CRUD, AI engines, analytics & chat
├── utils/
│   ├── __init__.py
│   ├── auth_helpers.py             # Session auth decorators & input validators
│   └── reminder_engine.py          # Dynamic exam/daily/pending/revision reminder sync
├── static/
│   ├── css/style.css               # Dark Navy, Purple & Light Cyan design system
│   └── js/                         # Page controllers & Chart.js integrations
│       ├── main.js
│       ├── landing.js
│       ├── dashboard.js
│       ├── subjects.js
│       ├── planner.js
│       ├── weak_topics.js
│       ├── assistant.js
│       ├── progress.js
│       └── reminders.js
├── templates/                      # Jinja2 HTML5 templates for all 9 pages
│   ├── base.html
│   ├── landing.html
│   ├── auth.html
│   ├── dashboard.html
│   ├── subjects.html
│   ├── planner.html
│   ├── weak_topics.html
│   ├── assistant.html
│   ├── progress.html
│   └── reminders.html
└── tests/
    └── test_app.py                 # End-to-end automated pytest suite
```

---

## Database Schema (8 MySQL Tables)

Defined in [`database/schema.sql`](database/schema.sql) and [`models/models.py`](models/models.py):
1. `Students`
2. `Subjects` (FK `student_id -> Students`)
3. `Topics` (FK `subject_id -> Subjects`, `student_id -> Students`)
4. `Exams` (FK `subject_id -> Subjects`, `student_id -> Students`)
5. `Study_Schedules` (FK `student_id -> Students`, `subject_id -> Subjects`, `topic_id -> Topics`)
6. `Study_Progress` (FK `student_id -> Students`, `subject_id -> Subjects`, `topic_id -> Topics`)
7. `Reminders` (FK `student_id -> Students`, `subject_id -> Subjects`, `topic_id -> Topics`, `exam_id -> Exams`)
8. `Quiz_Results` (FK `student_id -> Students`, `subject_id -> Subjects`, `topic_id -> Topics`)

---

## Installation & Local Setup

### 1. Prerequisites
- Python 3.10+
- MySQL Server 8.0+ (or MariaDB)

### 2. Create Virtual Environment & Install Dependencies
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure MySQL & Environment Variables
1. Start your MySQL Server locally (default port `3306`).
2. Copy `.env.example` to `.env` and update your MySQL credentials:
```powershell
Copy-Item .env.example .env
```
Edit `.env`:
```env
SECRET_KEY=your-secure-random-key
DB_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=smart_study_planner
ALLOW_SQLITE_FALLBACK=0
```

### 4. Initialize MySQL Database & Sample Student Data
**Option A (Recommended - Automated Python Initializer):**
```powershell
python database/init_db.py
```
This creates `smart_study_planner`, builds all 8 tables, and seeds sample college data.

**Option B (Direct MySQL CLI / Workbench):**
```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed_data.sql
```

### 5. Run the Web Application
```powershell
python app.py
```
Open your browser at **http://127.0.0.1:5000**

#### Sample Student Demo Login
- **Email:** `aarav.sharma@college.edu`
- **Password:** `StudySmart123!`

*(Tip: If you want to test the UI quickly without a running MySQL server, set `ALLOW_SQLITE_FALLBACK=1` in `.env`, run `python database/init_db.py`, and then run `python app.py`.)*

---

## Running Automated Tests
```powershell
.\venv\Scripts\python -m pytest -v
```

