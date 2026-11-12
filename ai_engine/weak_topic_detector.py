from datetime import date
from typing import Optional
from models import db, Topic, Subject, QuizResult


def compute_topic_weakness(
    topic: Topic,
    subject: Optional[Subject] = None,
    quiz_results: Optional[list[QuizResult]] = None,
) -> dict:
    """
    Compute composite weakness score (0-100, higher = weaker) and classify
    a topic into 'weak', 'average', or 'strong'.
    """
    subject = subject or topic.subject
    quizzes = quiz_results if quiz_results is not None else list(topic.quiz_results or [])

    rating = max(1, min(5, int(topic.understanding_rating or 3)))
    understanding_penalty = ((5 - rating) / 4.0) * 45.0  # 0..45

    avg_quiz_pct = None
    if quizzes:
        avg_quiz_pct = round(sum(q.percentage for q in quizzes) / len(quizzes), 1)
        quiz_penalty = ((100.0 - avg_quiz_pct) / 100.0) * 40.0  # 0..40
    else:
        quiz_penalty = 5.0 if topic.status == "completed" else 16.0

    difficulty = max(1, min(5, int(subject.difficulty_level if subject else 3)))
    difficulty_penalty = ((difficulty - 1) / 4.0) * 15.0  # 0..15

    decay_penalty = 0.0
    if topic.last_studied_at:
        days_since = (date.today() - topic.last_studied_at).days
        if days_since >= 10:
            decay_penalty = 8.0
        elif days_since >= 5:
            decay_penalty = 4.0

    weakness_score = round(min(100.0, understanding_penalty + quiz_penalty + difficulty_penalty + decay_penalty), 1)

    if weakness_score >= 56 or rating <= 2 or (avg_quiz_pct is not None and avg_quiz_pct < 60.0):
        level = "weak"
    elif weakness_score <= 28 and rating >= 4 and (avg_quiz_pct is None or avg_quiz_pct >= 80.0):
        level = "strong"
    else:
        level = "average"

    return {
        "weakness_score": weakness_score,
        "weakness_level": level,
        "avg_quiz_pct": avg_quiz_pct,
        "quiz_count": len(quizzes),
    }


def refresh_topic_weakness(topic: Topic) -> dict:
    """Recalculate and persist weakness_level on a Topic record."""
    metrics = compute_topic_weakness(topic)
    topic.weakness_level = metrics["weakness_level"]
    db.session.add(topic)
    return metrics


def analyze_student_topics(student_id: int) -> dict:
    """Return full weak/average/strong classification and counts for a student."""
    topics = (
        Topic.query.filter_by(student_id=student_id)
        .join(Subject, Topic.subject_id == Subject.subject_id)
        .all()
    )

    analyzed = []
    counts = {"weak": 0, "average": 0, "strong": 0}

    for topic in topics:
        metrics = compute_topic_weakness(topic, subject=topic.subject)
        if topic.weakness_level != metrics["weakness_level"]:
            topic.weakness_level = metrics["weakness_level"]
            db.session.add(topic)

        counts[metrics["weakness_level"]] += 1
        analyzed.append(
            {
                **topic.to_dict(),
                "subject_name": topic.subject.subject_name if topic.subject else "",
                "subject_priority": topic.subject.priority if topic.subject else "Medium",
                "difficulty_level": topic.subject.difficulty_level if topic.subject else 3,
                "weakness_score": metrics["weakness_score"],
                "avg_quiz_pct": metrics["avg_quiz_pct"],
                "quiz_count": metrics["quiz_count"],
            }
        )

    db.session.commit()
    analyzed.sort(key=lambda item: item["weakness_score"], reverse=True)

    return {
        "topics": analyzed,
        "summary": counts,
    }

