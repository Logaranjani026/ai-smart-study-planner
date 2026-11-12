import os
import sys
from datetime import date, timedelta
import pymysql

# Ensure workspace root is importable when run as `python database/init_db.py`
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv  # noqa: E402
from app import create_app  # noqa: E402
from models import (  # noqa: E402
    db,
    Student,
    Subject,
    Topic,
    Exam,
    StudyProgress,
    QuizResult,
)
from ai_engine import generate_smart_timetable, analyze_student_topics  # noqa: E402
from utils.reminder_engine import sync_student_reminders, refresh_exam_preparedness  # noqa: E402

load_dotenv()


def ensure_mysql_database_exists() -> None:
    """Create the MySQL database if it does not exist yet."""
    if os.getenv("ALLOW_SQLITE_FALLBACK", "0") == "1" or os.getenv("DATABASE_URL", "").startswith("sqlite"):
        return

    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    db_name = os.getenv("MYSQL_DATABASE", "smart_study_planner")

    conn = pymysql.connect(host=host, port=port, user=user, password=password, charset="utf8mb4")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        conn.commit()
    finally:
        conn.close()


def seed_sample_data() -> None:
    """Populate realistic college student data across all 8 tables idempotently."""
    sample_email = "aarav.sharma@college.edu"
    if Student.query.filter_by(email=sample_email).first():
        print("Sample student data already present. Skipping seed.")
        return

    today = date.today()

    student = Student(
        full_name="Aarav Sharma",
        email=sample_email,
        department="Computer Science & Engineering",
        year_of_study="3rd Year",
        daily_study_goal_hours=4.0,
        preferred_study_time="evening",
    )
    student.set_password("StudySmart123!")
    db.session.add(student)
    db.session.flush()

    subjects_spec = [
        {
            "name": "Data Structures & Algorithms",
            "code": "CS301",
            "difficulty": 5,
            "priority": "High",
            "color": "#6d28d9",
            "target": 8.0,
            "exam": ("Midterm Exam", today + timedelta(days=5), "09:00", "Trees, Graphs, and Dynamic Programming"),
            "topics": [
                ("Chapter 1: Trees", "Binary Search Trees & AVL Rotations", 2.0, "completed", 5, today - timedelta(days=3)),
                ("Chapter 2: Graphs", "Dijkstra & Shortest Paths", 2.5, "in_progress", 2, today - timedelta(days=2)),
                ("Chapter 3: Dynamic Programming", "0/1 Knapsack & Memoization", 3.0, "pending", 1, today - timedelta(days=6)),
                ("Chapter 3: Dynamic Programming", "Longest Common Subsequence", 2.0, "pending", 2, None),
            ],
        },
        {
            "name": "Database Management Systems",
            "code": "CS304",
            "difficulty": 3,
            "priority": "High",
            "color": "#06b6d4",
            "target": 6.0,
            "exam": ("DBMS Quiz & Lab Exam", today + timedelta(days=11), "14:00", "Normalization, SQL Joins, and B+ Trees"),
            "topics": [
                ("Chapter 1: Relational Design", "ER Diagrams & Keys", 1.5, "completed", 5, today - timedelta(days=4)),
                ("Chapter 2: Normalization", "1NF to BCNF Decomposition", 2.0, "completed", 3, today - timedelta(days=1)),
                ("Chapter 3: Storage & Indexing", "B+ Tree Indexing & Hashing", 2.5, "pending", 2, None),
            ],
        },
        {
            "name": "Operating Systems",
            "code": "CS302",
            "difficulty": 4,
            "priority": "Medium",
            "color": "#0b1437",
            "target": 5.0,
            "exam": ("OS Unit Test", today + timedelta(days=16), "10:30", "CPU Scheduling & Deadlocks"),
            "topics": [
                ("Chapter 1: Processes", "CPU Scheduling Algorithms", 2.0, "completed", 4, today - timedelta(days=5)),
                ("Chapter 2: Synchronization", "Deadlock Prevention & Banker's Algorithm", 2.5, "in_progress", 2, today - timedelta(days=2)),
            ],
        },
        {
            "name": "Linear Algebra",
            "code": "MA204",
            "difficulty": 4,
            "priority": "Medium",
            "color": "#059669",
            "target": 5.0,
            "exam": ("Linear Algebra Midterm", today + timedelta(days=9), "11:00", "Vector Spaces & Eigenvalues"),
            "topics": [
                ("Chapter 1: Matrices", "Gaussian Elimination & Rank", 1.5, "completed", 4, today - timedelta(days=6)),
                ("Chapter 2: Eigenvalues", "Eigenvalues & Diagonalization", 2.5, "pending", 2, today - timedelta(days=3)),
            ],
        },
    ]

    topic_lookup: dict[str, Topic] = {}
    subj_lookup: dict[str, Subject] = {}

    for spec in subjects_spec:
        subj = Subject(
            student_id=student.student_id,
            subject_name=spec["name"],
            subject_code=spec["code"],
            difficulty_level=spec["difficulty"],
            priority=spec["priority"],
            color_tag=spec["color"],
            target_hours_per_week=spec["target"],
        )
        db.session.add(subj)
        db.session.flush()
        subj_lookup[spec["code"]] = subj

        ex_title, ex_date, ex_time, ex_notes = spec["exam"]
        db.session.add(
            Exam(
                student_id=student.student_id,
                subject_id=subj.subject_id,
                exam_title=ex_title,
                exam_date=ex_date,
                exam_time=ex_time,
                syllabus_notes=ex_notes,
            )
        )

        for ch, t_name, est_h, st, rating, last_dt in spec["topics"]:
            t = Topic(
                subject_id=subj.subject_id,
                student_id=student.student_id,
                chapter_name=ch,
                topic_name=t_name,
                estimated_hours=est_h,
                status=st,
                understanding_rating=rating,
                last_studied_at=last_dt,
            )
            db.session.add(t)
            db.session.flush()
            topic_lookup[t_name] = t

    # Sample Quiz Results
    quiz_entries = [
        ("Binary Search Trees & AVL Rotations", "Trees Practice Quiz", 9.0, 10.0, "Easy"),
        ("Dijkstra & Shortest Paths", "Graph Traversal Check", 4.5, 10.0, "Hard"),
        ("0/1 Knapsack & Memoization", "DP Diagnostic Quiz", 3.5, 10.0, "Hard"),
        ("1NF to BCNF Decomposition", "Normalization Sprint", 7.0, 10.0, "Medium"),
        ("CPU Scheduling Algorithms", "Scheduling Quiz", 8.5, 10.0, "Easy"),
        ("Deadlock Prevention & Banker's Algorithm", "Synchronization Quiz", 5.0, 10.0, "Hard"),
    ]
    for t_name, q_title, sc, mx, fb in quiz_entries:
        t = topic_lookup[t_name]
        db.session.add(
            QuizResult(
                student_id=student.student_id,
                subject_id=t.subject_id,
                topic_id=t.topic_id,
                quiz_title=q_title,
                score=sc,
                max_score=mx,
                percentage=round((sc / mx) * 100.0, 1),
                difficulty_feedback=fb,
            )
        )

    # Sample Study Progress over the last 7 days
    progress_entries = [
        (6, "CS301", "Binary Search Trees & AVL Rotations", 2.0, 1, 5, "Completed AVL rotations practice"),
        (5, "CS302", "CPU Scheduling Algorithms", 2.5, 1, 4, "Solved Round Robin Gantt charts"),
        (4, "CS304", "ER Diagrams & Keys", 2.0, 1, 5, "Designed college schema diagrams"),
        (3, "MA204", "Eigenvalues & Diagonalization", 1.5, 0, 3, "Reviewed characteristic equations"),
        (2, "CS301", "Dijkstra & Shortest Paths", 2.5, 0, 3, "Struggled slightly with negative edge cases"),
        (1, "CS304", "1NF to BCNF Decomposition", 3.0, 1, 4, "Completed normalization worksheet"),
        (0, "CS302", "Deadlock Prevention & Banker's Algorithm", 1.5, 0, 4, "Worked through safety algorithm"),
    ]
    for days_ago, code, t_name, hrs, done_cnt, focus, notes in progress_entries:
        subj = subj_lookup[code]
        t = topic_lookup[t_name]
        db.session.add(
            StudyProgress(
                student_id=student.student_id,
                subject_id=subj.subject_id,
                topic_id=t.topic_id,
                study_date=today - timedelta(days=days_ago),
                hours_studied=hrs,
                topics_completed_count=done_cnt,
                focus_rating=focus,
                notes=notes,
            )
        )

    db.session.commit()

    # Run AI engines to populate weakness levels, timetable, preparedness & reminders
    analyze_student_topics(student.student_id)
    refresh_exam_preparedness(student.student_id)
    generate_smart_timetable(
        student_id=student.student_id,
        weekday_hours=4.0,
        weekend_hours=6.0,
        preferred_time="evening",
        focus_strategy="balanced",
        session_duration=1.5,
        days=7,
    )
    sync_student_reminders(student)
    print(f"Seeded sample student '{sample_email}' (password: StudySmart123!) across all 8 tables.")


def init_database() -> None:
    ensure_mysql_database_exists()
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_sample_data()


if __name__ == "__main__":
    init_database()

