from datetime import date, timedelta
from typing import Optional
from models import db, Topic, Exam


INTERVAL_MAP = {
    "weak": [1, 2, 4, 7, 12],
    "average": [2, 4, 8, 15, 25],
    "strong": [4, 9, 18, 30, 45],
}


def predict_topic_next_revision(
    topic: Topic,
    earliest_exam_date: Optional[date] = None,
    reference_date: Optional[date] = None,
) -> tuple[date, str]:
    """
    Smart Revision Predictor using spaced repetition curves adjusted by
    topic weakness and upcoming exam proximity.
    """
    today = reference_date or date.today()
    level = topic.weakness_level or "average"
    intervals = INTERVAL_MAP.get(level, INTERVAL_MAP["average"])
    idx = min(max(0, int(topic.revision_count or 0)), len(intervals) - 1)
    days_interval = intervals[idx]

    base_date = topic.last_studied_at or today
    candidate = base_date + timedelta(days=days_interval)
    if candidate < today:
        candidate = today

    reason = f"Spaced interval (Day {days_interval}) for {level} topic"

    if earliest_exam_date and earliest_exam_date >= today:
        safe_pre_exam = max(today, earliest_exam_date - timedelta(days=2))
        if candidate > safe_pre_exam:
            candidate = safe_pre_exam
            reason = f"Pulled forward ahead of exam on {earliest_exam_date.isoformat()}"

    return candidate, reason


def get_revision_recommendations(student_id: int, limit: int = 8) -> list[dict]:
    """Return prioritized revision recommendations and sync next_revision_date."""
    today = date.today()
    topics = Topic.query.filter_by(student_id=student_id).all()
    exams = Exam.query.filter(
        Exam.student_id == student_id,
        Exam.exam_date >= today,
    ).all()

    earliest_exam_by_subject: dict[int, date] = {}
    for ex in exams:
        cur = earliest_exam_by_subject.get(ex.subject_id)
        if cur is None or ex.exam_date < cur:
            earliest_exam_by_subject[ex.subject_id] = ex.exam_date

    recommendations = []
    for topic in topics:
        # Recommend revision for studied/completed topics OR weak topics
        if topic.status == "pending" and topic.weakness_level != "weak" and not topic.last_studied_at:
            continue

        exam_date = earliest_exam_by_subject.get(topic.subject_id)
        rec_date, reason = predict_topic_next_revision(topic, earliest_exam_date=exam_date, reference_date=today)
        topic.next_revision_date = rec_date
        db.session.add(topic)

        days_until = (rec_date - today).days
        if days_until <= 0 or topic.weakness_level == "weak":
            urgency = "high"
        elif days_until <= 3:
            urgency = "medium"
        else:
            urgency = "low"

        recommendations.append(
            {
                "topic_id": topic.topic_id,
                "subject_id": topic.subject_id,
                "subject_name": topic.subject.subject_name if topic.subject else "",
                "topic_name": topic.topic_name,
                "weakness_level": topic.weakness_level,
                "recommended_date": rec_date.isoformat(),
                "days_until": days_until,
                "urgency": urgency,
                "reason": reason,
            }
        )

    db.session.commit()
    recommendations.sort(key=lambda r: (r["days_until"], 0 if r["weakness_level"] == "weak" else 1))
    return recommendations[:limit]

