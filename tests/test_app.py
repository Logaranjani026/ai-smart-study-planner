import os
import re
from datetime import date, timedelta
import pytest

from app import create_app
from models import db


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_study_planner.db"
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
            "SECRET_KEY": "test-secret",
        }
    )
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def register_and_login(client, email="student1@college.edu", name="Student One"):
    res = client.post(
        "/api/auth/register",
        json={
            "full_name": name,
            "email": email,
            "password": "Password123!",
            "department": "Computer Science & Engineering",
            "year_of_study": "3rd Year",
        },
    )
    assert res.status_code == 201
    return res.get_json()["student"]


def test_schema_contains_all_eight_mysql_tables():
    schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    expected_tables = [
        "Students",
        "Subjects",
        "Topics",
        "Study_Schedules",
        "Study_Progress",
        "Exams",
        "Reminders",
        "Quiz_Results",
    ]
    for tbl in expected_tables:
        assert re.search(rf"CREATE TABLE IF NOT EXISTS {tbl}\b", sql), f"Missing {tbl} in schema.sql"
        assert tbl in db.metadata.tables, f"Missing {tbl} in SQLAlchemy models"

    seed_path = os.path.join(os.path.dirname(__file__), "..", "database", "seed_data.sql")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_sql = f.read()
    assert "aarav.sharma@college.edu" in seed_sql


def test_auth_registration_login_and_password_reset(client):
    landing = client.get("/")
    assert landing.status_code == 200
    assert b"Study Smarter," in landing.data
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/forgot-password").status_code == 200

    # Validation failure
    bad = client.post("/api/auth/register", json={"full_name": "A", "email": "bad", "password": "123"})
    assert bad.status_code == 400

    # Register student
    register_and_login(client, email="alice@college.edu", name="Alice Roy")

    # Duplicate email prevented
    dup = client.post(
        "/api/auth/register",
        json={
            "full_name": "Alice Two",
            "email": "alice@college.edu",
            "password": "Password123!",
            "department": "IT",
            "year_of_study": "2nd Year",
        },
    )
    assert dup.status_code == 409

    # Logout & verify protected redirect
    client.get("/logout")
    assert client.get("/dashboard").status_code == 302
    assert client.get("/api/dashboard").status_code == 401

    # Forgot password & reset
    forgot = client.post("/api/auth/forgot-password", json={"email": "alice@college.edu"})
    assert forgot.status_code == 200
    token = forgot.get_json()["reset_token"]

    reset = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPassword456!"},
    )
    assert reset.status_code == 200

    # Login with new password
    login_res = client.post(
        "/api/auth/login",
        json={"email": "alice@college.edu", "password": "NewPassword456!"},
    )
    assert login_res.status_code == 200


def test_student_data_isolation(client):
    register_and_login(client, email="usera@college.edu", name="User A")
    subj_res = client.post(
        "/api/subjects",
        json={"subject_name": "Algorithms", "priority": "High", "difficulty_level": 4},
    )
    assert subj_res.status_code == 201
    subj_id = subj_res.get_json()["subject"]["subject_id"]
    topic_res = client.post(
        f"/api/subjects/{subj_id}/topics",
        json={"chapter_name": "Ch1", "topic_name": "Sorting", "estimated_hours": 2},
    )
    topic_id = topic_res.get_json()["topic"]["topic_id"]

    # Switch to User B
    client.get("/logout")
    register_and_login(client, email="userb@college.edu", name="User B")

    assert client.get("/api/subjects").get_json()["subjects"] == []
    assert client.put(f"/api/subjects/{subj_id}", json={"subject_name": "Hacked"}).status_code == 404
    assert client.delete(f"/api/subjects/{subj_id}").status_code == 404
    assert client.patch(f"/api/topics/{topic_id}/rating", json={"understanding_rating": 1}).status_code == 404
    assert client.post("/api/quizzes", json={"topic_id": topic_id, "score": 5, "max_score": 10}).status_code == 404


def test_full_study_workflow_and_crud(client):
    register_and_login(client, email="fulltest@college.edu", name="Rohan Verma")
    soon_date = (date.today() + timedelta(days=4)).isoformat()

    # 1. Create & Update Subject with Exam Date
    s_res = client.post(
        "/api/subjects",
        json={
            "subject_name": "Data Structures",
            "subject_code": "CS201",
            "priority": "High",
            "difficulty_level": 5,
            "target_hours_per_week": 8,
            "exam_date": soon_date,
            "exam_title": "Midterm Exam",
        },
    )
    assert s_res.status_code == 201
    subj_id = s_res.get_json()["subject"]["subject_id"]

    assert client.put(f"/api/subjects/{subj_id}", json={"priority": "Medium"}).status_code == 200

    # Add & delete extra exam
    ex2 = client.post(
        "/api/exams",
        json={"subject_id": subj_id, "exam_title": "Lab Exam", "exam_date": soon_date},
    )
    assert ex2.status_code == 201
    ex2_id = ex2.get_json()["exam"]["exam_id"]
    assert client.delete(f"/api/exams/{ex2_id}").status_code == 200

    # 2. Add, edit, rate & delete Topics
    t1_res = client.post(
        f"/api/subjects/{subj_id}/topics",
        json={
            "chapter_name": "Chapter 1",
            "topic_name": "Dynamic Programming",
            "estimated_hours": 3,
            "understanding_rating": 1,
        },
    )
    assert t1_res.status_code == 201
    t1_id = t1_res.get_json()["topic"]["topic_id"]

    t2_res = client.post(
        f"/api/subjects/{subj_id}/topics",
        json={
            "chapter_name": "Chapter 2",
            "topic_name": "Binary Trees",
            "estimated_hours": 2,
            "status": "completed",
            "understanding_rating": 5,
        },
    )
    assert t2_res.status_code == 201
    t2_id = t2_res.get_json()["topic"]["topic_id"]

    assert client.put(f"/api/topics/{t2_id}", json={"estimated_hours": 2.5}).status_code == 200
    assert client.patch(f"/api/topics/{t1_id}/rating", json={"understanding_rating": 2}).status_code == 200

    # 3. Weak Topic Detector + Quiz Validation & Recording
    bad_quiz = client.post(
        "/api/quizzes",
        json={"topic_id": t1_id, "quiz_title": "Invalid", "score": 15, "max_score": 10},
    )
    assert bad_quiz.status_code == 400

    q_res = client.post(
        "/api/quizzes",
        json={
            "topic_id": t1_id,
            "quiz_title": "DP Diagnostic",
            "score": 3,
            "max_score": 10,
            "difficulty_feedback": "Hard",
        },
    )
    assert q_res.status_code == 201
    assert q_res.get_json()["topic_metrics"]["weakness_level"] == "weak"

    weak_res = client.get("/api/weak-topics").get_json()
    assert weak_res["summary"]["weak"] >= 1
    assert len(weak_res["revision_recommendations"]) >= 1

    # Schedule revision slot directly
    rev_slot = client.post("/api/planner/revision-slot", json={"topic_id": t1_id, "study_date": soon_date})
    assert rev_slot.status_code == 201

    # 4. Smart Timetable Generator & Adaptive Planner
    plan_res = client.post(
        "/api/planner/generate",
        json={
            "weekday_hours": 4,
            "weekend_hours": 6,
            "preferred_time": "evening",
            "focus_strategy": "weak_first",
            "session_duration": 1.5,
            "days": 7,
        },
    )
    assert plan_res.status_code == 200
    schedules = plan_res.get_json()["schedules"]
    assert len(schedules) >= 4

    first_id = schedules[0]["schedule_id"]
    second_id = schedules[1]["schedule_id"]

    assert client.patch(f"/api/schedules/{first_id}/status", json={"status": "completed"}).status_code == 200
    assert client.patch(f"/api/schedules/{second_id}/status", json={"status": "missed"}).status_code == 200

    adapt_res = client.post("/api/planner/adapt", json={"weekday_hours": 4})
    assert adapt_res.status_code == 200
    assert adapt_res.get_json()["rescheduled_missed_count"] == 1

    # 5. Progress Tracking & Analytics
    assert client.post("/api/progress", json={"subject_id": subj_id, "hours_studied": -1}).status_code == 400
    prog_res = client.post(
        "/api/progress",
        json={"subject_id": subj_id, "topic_id": t1_id, "hours_studied": 2.0, "focus_rating": 5},
    )
    assert prog_res.status_code == 201

    analytics = client.get("/api/progress/analytics").get_json()
    assert analytics["summary"]["today_hours"] >= 2.0
    assert analytics["summary"]["streak_days"] >= 1

    # 6. Dashboard API
    dash = client.get("/api/dashboard").get_json()
    assert dash["kpis"]["total_subjects"] == 1
    assert len(dash["upcoming_exams"]) == 1
    assert len(dash["ai_suggestions"]) >= 1

    # 7. AI Study Assistant
    chat1 = client.post("/api/assistant/chat", json={"message": "Explain Dynamic Programming"}).get_json()
    assert "Dynamic Programming" in chat1["reply"]
    chat2 = client.post("/api/assistant/chat", json={"message": "What should I revise today?"}).get_json()
    assert "Smart Revision Predictor" in chat2["reply"] or "Dynamic Programming" in chat2["reply"]
    chat3 = client.post("/api/assistant/chat", json={"message": "Organize my timetable"}).get_json()
    assert "Today's Plan" in chat3["reply"]

    # 8. Reminder System
    sync_res = client.post("/api/reminders/sync")
    assert sync_res.status_code == 200
    rem_list = client.get("/api/reminders").get_json()["reminders"]
    assert any(r["reminder_type"] == "exam" for r in rem_list)

    custom_rem = client.post(
        "/api/reminders",
        json={"title": "Submit Lab", "message": "Upload PDF", "due_date": soon_date, "priority": "high"},
    )
    assert custom_rem.status_code == 201
    rem_id = custom_rem.get_json()["reminder"]["reminder_id"]
    assert client.patch(f"/api/reminders/{rem_id}", json={"is_completed": True}).status_code == 200
    assert client.delete(f"/api/reminders/{rem_id}").status_code == 200

    # 9. Verify all authenticated HTML pages render 200 OK
    for path in ["/dashboard", "/subjects", "/planner", "/weak-topics", "/assistant", "/progress", "/reminders"]:
        page_res = client.get(path)
        assert page_res.status_code == 200, f"Failed page {path}"

    # 10. Delete Topic and Subject cleanly
    assert client.delete(f"/api/topics/{t2_id}").status_code == 200
    assert client.delete(f"/api/subjects/{subj_id}").status_code == 200
