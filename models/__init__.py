from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from models.models import (  # noqa: E402, F401
    Student,
    Subject,
    Topic,
    StudySchedule,
    StudyProgress,
    Exam,
    Reminder,
    QuizResult,
)

__all__ = [
    "db",
    "Student",
    "Subject",
    "Topic",
    "StudySchedule",
    "StudyProgress",
    "Exam",
    "Reminder",
    "QuizResult",
]

