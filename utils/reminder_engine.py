from datetime import date
from models import db, Exam, Topic, StudyProgress, StudySchedule, Reminder, Subject
from ai_engine.revision_predictor import get_revision_recommendations


def refresh_exam_preparedness(student_id: int) -> None:
    """Update preparedness_score for each exam based on subject topic mastery."""
    exams = Exam.query.filter_by(student_id=student_id).all()
    for ex in exams:
        topics = Topic.query.filter_by(student_id=student_id, subject_id=ex.subject_id).all()
        if not topics:
            ex.preparedness_score = 40
        else:
            completed = sum(1 for t in topics if t.status == "completed")
            avg_rating = sum(t.understanding_rating for t in topics) / len(topics)
            completion_component = (completed / len(topics)) * 60.0
            rating_component = (avg_rating / 5.0) * 40.0
            ex.preparedness_score = int(round(min(100.0, completion_component + rating_component)))
        db.session.add(ex)
    db.session.commit()


def _upsert_auto_reminder(
    student_id: int,
    reminder_type: str,
    title: str,
    message: str,
    due_date: date,
    priority: str = "medium",
    subject_id: int | None = None,
    topic_id: int | None = None,
    exam_id: int | None = None,
) -> Reminder:
    existing = Reminder.query.filter_by(
        student_id=student_id,
        reminder_type=reminder_type,
        title=title,
        is_completed=False,
    ).first()
    if existing:
        existing.message = message
        existing.due_date = due_date
        existing.priority = priority
        db.session.add(existing)
        return existing

    rem = Reminder(
        student_id=student_id,
        subject_id=subject_id,
        topic_id=topic_id,
        exam_id=exam_id,
        reminder_type=reminder_type,
        title=title,
        message=message,
        due_date=due_date,
        priority=priority,
        is_auto_generated=True,
    )
    db.session.add(rem)
    return rem


def sync_student_reminders(student) -> int:
    """
    Generate or refresh dynamic reminders for:
    1. Upcoming exams
    2. Daily study goals
    3. High-priority pending topics
    4. Smart Revision Predictor due topics
    """
    today = date.today()
    student_id = student.student_id
    synced = 0

    # 1. Upcoming Exams within 14 days
    exams = Exam.query.filter(
        Exam.student_id == student_id,
        Exam.exam_date >= today,
    ).all()
    for ex in exams:
        days_left = (ex.exam_date - today).days
        if days_left <= 14:
            subj_name = ex.subject.subject_name if ex.subject else "Subject"
            prio = "high" if days_left <= 5 else "medium"
            _upsert_auto_reminder(
                student_id=student_id,
                reminder_type="exam",
                title=f"Exam Alert: {subj_name} ({ex.exam_title})",
                message=f"Exam in {days_left} day(s) on {ex.exam_date.isoformat()}. Current readiness: {ex.preparedness_score}%.",
                due_date=ex.exam_date,
                priority=prio,
                subject_id=ex.subject_id,
                exam_id=ex.exam_id,
            )
            synced += 1

    # 2. Daily Study Goal Reminder
    logged_today = sum(
        p.hours_studied
        for p in StudyProgress.query.filter_by(student_id=student_id, study_date=today).all()
    )
    planned_today = StudySchedule.query.filter_by(
        student_id=student_id, study_date=today, status="scheduled"
    ).count()
    if logged_today < student.daily_study_goal_hours:
        remaining = round(student.daily_study_goal_hours - logged_today, 1)
        _upsert_auto_reminder(
            student_id=student_id,
            reminder_type="daily_study",
            title=f"Daily Study Goal ({today.isoformat()})",
            message=f"You have {remaining} hr(s) remaining toward your {student.daily_study_goal_hours}h daily target ({planned_today} block(s) scheduled today).",
            due_date=today,
            priority="medium",
        )
        synced += 1

    # 3. High-Priority Pending Topics
    pending_high = (
        Topic.query.join(Subject, Topic.subject_id == Subject.subject_id)
        .filter(
            Topic.student_id == student_id,
            Topic.status != "completed",
            Subject.priority == "High",
        )
        .limit(3)
        .all()
    )
    for topic in pending_high:
        _upsert_auto_reminder(
            student_id=student_id,
            reminder_type="pending_topic",
            title=f"Pending High-Priority Topic: {topic.topic_name}",
            message=f"{topic.subject.subject_name} ({topic.chapter_name}) is still {topic.status}. Allocate a study block soon.",
            due_date=today,
            priority="medium",
            subject_id=topic.subject_id,
            topic_id=topic.topic_id,
        )
        synced += 1

    # 4. Smart Revision Predictor due reminders (<= 2 days)
    revs = get_revision_recommendations(student_id, limit=5)
    for rec in revs:
        if rec["days_until"] <= 2:
            _upsert_auto_reminder(
                student_id=student_id,
                reminder_type="revision",
                title=f"Revision Due: {rec['topic_name']}",
                message=f"{rec['subject_name']} — {rec['reason']}. Target revision date: {rec['recommended_date']}.",
                due_date=date.fromisoformat(rec["recommended_date"]),
                priority="high" if rec["weakness_level"] == "weak" else "medium",
                subject_id=rec["subject_id"],
                topic_id=rec["topic_id"],
            )
            synced += 1

    db.session.commit()
    return synced

