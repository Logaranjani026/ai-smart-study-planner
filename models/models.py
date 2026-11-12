from datetime import datetime, date, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Student(db.Model):
    __tablename__ = "Students"

    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    department = db.Column(db.String(120), nullable=False)
    year_of_study = db.Column(db.String(40), nullable=False)
    daily_study_goal_hours = db.Column(db.Float, nullable=False, default=4.0)
    preferred_study_time = db.Column(
        db.Enum("morning", "afternoon", "evening", name="preferred_time_enum"),
        nullable=False,
        default="evening",
    )
    reset_token = db.Column(db.String(120), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    subjects = db.relationship("Subject", backref="student", cascade="all, delete-orphan", lazy=True)
    topics = db.relationship("Topic", backref="student", cascade="all, delete-orphan", lazy=True)
    schedules = db.relationship("StudySchedule", backref="student", cascade="all, delete-orphan", lazy=True)
    progress_logs = db.relationship("StudyProgress", backref="student", cascade="all, delete-orphan", lazy=True)
    exams = db.relationship("Exam", backref="student", cascade="all, delete-orphan", lazy=True)
    reminders = db.relationship("Reminder", backref="student", cascade="all, delete-orphan", lazy=True)
    quiz_results = db.relationship("QuizResult", backref="student", cascade="all, delete-orphan", lazy=True)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password, method="pbkdf2:sha256")

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "full_name": self.full_name,
            "email": self.email,
            "department": self.department,
            "year_of_study": self.year_of_study,
            "daily_study_goal_hours": self.daily_study_goal_hours,
            "preferred_study_time": self.preferred_study_time,
        }


class Subject(db.Model):
    __tablename__ = "Subjects"

    subject_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_name = db.Column(db.String(140), nullable=False)
    subject_code = db.Column(db.String(30), nullable=True)
    difficulty_level = db.Column(db.Integer, nullable=False, default=3)  # 1..5
    priority = db.Column(
        db.Enum("High", "Medium", "Low", name="subject_priority_enum"),
        nullable=False,
        default="Medium",
    )
    color_tag = db.Column(db.String(20), nullable=False, default="#6d28d9")
    target_hours_per_week = db.Column(db.Float, nullable=False, default=6.0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    topics = db.relationship("Topic", backref="subject", cascade="all, delete-orphan", lazy=True)
    exams = db.relationship("Exam", backref="subject", cascade="all, delete-orphan", lazy=True)
    schedules = db.relationship("StudySchedule", backref="subject", cascade="all, delete-orphan", lazy=True)
    progress_logs = db.relationship("StudyProgress", backref="subject", cascade="all, delete-orphan", lazy=True)
    quiz_results = db.relationship("QuizResult", backref="subject", cascade="all, delete-orphan", lazy=True)

    def to_dict(self, include_children: bool = False) -> dict:
        data = {
            "subject_id": self.subject_id,
            "student_id": self.student_id,
            "subject_name": self.subject_name,
            "subject_code": self.subject_code,
            "difficulty_level": self.difficulty_level,
            "priority": self.priority,
            "color_tag": self.color_tag,
            "target_hours_per_week": self.target_hours_per_week,
        }
        if include_children:
            data["topics"] = [t.to_dict() for t in self.topics]
            data["exams"] = [e.to_dict() for e in sorted(self.exams, key=lambda x: x.exam_date)]
        return data


class Topic(db.Model):
    __tablename__ = "Topics"

    topic_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subject_id = db.Column(
        db.Integer, db.ForeignKey("Subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    chapter_name = db.Column(db.String(140), nullable=False)
    topic_name = db.Column(db.String(180), nullable=False)
    estimated_hours = db.Column(db.Float, nullable=False, default=2.0)
    status = db.Column(
        db.Enum("pending", "in_progress", "completed", name="topic_status_enum"),
        nullable=False,
        default="pending",
    )
    understanding_rating = db.Column(db.Integer, nullable=False, default=3)  # 1..5
    weakness_level = db.Column(
        db.Enum("weak", "average", "strong", name="weakness_level_enum"),
        nullable=False,
        default="average",
    )
    last_studied_at = db.Column(db.Date, nullable=True)
    next_revision_date = db.Column(db.Date, nullable=True)
    revision_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    quiz_results = db.relationship("QuizResult", backref="topic", cascade="all, delete-orphan", lazy=True)

    def to_dict(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "subject_id": self.subject_id,
            "student_id": self.student_id,
            "chapter_name": self.chapter_name,
            "topic_name": self.topic_name,
            "estimated_hours": self.estimated_hours,
            "status": self.status,
            "understanding_rating": self.understanding_rating,
            "weakness_level": self.weakness_level,
            "last_studied_at": self.last_studied_at.isoformat() if self.last_studied_at else None,
            "next_revision_date": self.next_revision_date.isoformat() if self.next_revision_date else None,
            "revision_count": self.revision_count,
        }


class StudySchedule(db.Model):
    __tablename__ = "Study_Schedules"

    schedule_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey("Subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id = db.Column(
        db.Integer, db.ForeignKey("Topics.topic_id", ondelete="SET NULL"), nullable=True
    )
    study_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    duration_hours = db.Column(db.Float, nullable=False, default=1.0)
    session_type = db.Column(
        db.Enum("learning", "revision", "practice", "exam_prep", name="session_type_enum"),
        nullable=False,
        default="learning",
    )
    priority_score = db.Column(db.Float, nullable=False, default=50.0)
    is_ai_generated = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(
        db.Enum("scheduled", "completed", "missed", "rescheduled", name="schedule_status_enum"),
        nullable=False,
        default="scheduled",
    )
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    topic = db.relationship("Topic", lazy=True)

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "subject_name": self.subject.subject_name if self.subject else "",
            "color_tag": self.subject.color_tag if self.subject else "#6d28d9",
            "topic_id": self.topic_id,
            "topic_name": self.topic.topic_name if self.topic else None,
            "study_date": self.study_date.isoformat(),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_hours": self.duration_hours,
            "session_type": self.session_type,
            "priority_score": round(self.priority_score, 1),
            "is_ai_generated": self.is_ai_generated,
            "status": self.status,
            "notes": self.notes,
        }


class StudyProgress(db.Model):
    __tablename__ = "Study_Progress"

    progress_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey("Subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id = db.Column(
        db.Integer, db.ForeignKey("Topics.topic_id", ondelete="SET NULL"), nullable=True
    )
    study_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    hours_studied = db.Column(db.Float, nullable=False, default=1.0)
    topics_completed_count = db.Column(db.Integer, nullable=False, default=0)
    focus_rating = db.Column(db.Integer, nullable=False, default=4)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    topic = db.relationship("Topic", lazy=True)

    def to_dict(self) -> dict:
        return {
            "progress_id": self.progress_id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "subject_name": self.subject.subject_name if self.subject else "",
            "topic_id": self.topic_id,
            "topic_name": self.topic.topic_name if self.topic else None,
            "study_date": self.study_date.isoformat(),
            "hours_studied": self.hours_studied,
            "topics_completed_count": self.topics_completed_count,
            "focus_rating": self.focus_rating,
            "notes": self.notes,
        }


class Exam(db.Model):
    __tablename__ = "Exams"

    exam_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey("Subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True
    )
    exam_title = db.Column(db.String(140), nullable=False)
    exam_date = db.Column(db.Date, nullable=False, index=True)
    exam_time = db.Column(db.String(15), nullable=True, default="09:00")
    syllabus_notes = db.Column(db.String(255), nullable=True)
    preparedness_score = db.Column(db.Integer, nullable=False, default=50)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self) -> dict:
        days_left = (self.exam_date - date.today()).days
        return {
            "exam_id": self.exam_id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "subject_name": self.subject.subject_name if self.subject else "",
            "exam_title": self.exam_title,
            "exam_date": self.exam_date.isoformat(),
            "exam_time": self.exam_time,
            "syllabus_notes": self.syllabus_notes,
            "preparedness_score": self.preparedness_score,
            "days_left": days_left,
        }


class Reminder(db.Model):
    __tablename__ = "Reminders"

    reminder_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey("Subjects.subject_id", ondelete="SET NULL"), nullable=True
    )
    topic_id = db.Column(
        db.Integer, db.ForeignKey("Topics.topic_id", ondelete="SET NULL"), nullable=True
    )
    exam_id = db.Column(
        db.Integer, db.ForeignKey("Exams.exam_id", ondelete="SET NULL"), nullable=True
    )
    reminder_type = db.Column(
        db.Enum("exam", "daily_study", "pending_topic", "revision", "custom", name="reminder_type_enum"),
        nullable=False,
        default="custom",
    )
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.String(350), nullable=False)
    due_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    priority = db.Column(
        db.Enum("high", "medium", "low", name="reminder_priority_enum"),
        nullable=False,
        default="medium",
    )
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    is_auto_generated = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self) -> dict:
        return {
            "reminder_id": self.reminder_id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "topic_id": self.topic_id,
            "exam_id": self.exam_id,
            "reminder_type": self.reminder_type,
            "title": self.title,
            "message": self.message,
            "due_date": self.due_date.isoformat(),
            "priority": self.priority,
            "is_read": self.is_read,
            "is_completed": self.is_completed,
            "is_auto_generated": self.is_auto_generated,
        }


class QuizResult(db.Model):
    __tablename__ = "Quiz_Results"

    quiz_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("Students.student_id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id = db.Column(
        db.Integer, db.ForeignKey("Subjects.subject_id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id = db.Column(
        db.Integer, db.ForeignKey("Topics.topic_id", ondelete="CASCADE"), nullable=False, index=True
    )
    quiz_title = db.Column(db.String(160), nullable=False)
    score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False, default=10.0)
    percentage = db.Column(db.Float, nullable=False)
    difficulty_feedback = db.Column(db.String(40), nullable=True, default="Medium")
    taken_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    def to_dict(self) -> dict:
        return {
            "quiz_id": self.quiz_id,
            "student_id": self.student_id,
            "subject_id": self.subject_id,
            "topic_id": self.topic_id,
            "quiz_title": self.quiz_title,
            "score": self.score,
            "max_score": self.max_score,
            "percentage": round(self.percentage, 1),
            "difficulty_feedback": self.difficulty_feedback,
            "taken_at": self.taken_at.isoformat(),
        }
