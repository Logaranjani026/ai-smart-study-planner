from datetime import date, timedelta
from flask import Blueprint, request, jsonify
from models import db, Subject, Topic, StudySchedule, StudyProgress, Exam, Reminder, QuizResult
from utils.auth_helpers import login_required_api, parse_date_str
from utils.reminder_engine import sync_student_reminders, refresh_exam_preparedness
from ai_engine import (
    analyze_student_topics,
    refresh_topic_weakness,
    get_revision_recommendations,
    generate_smart_timetable,
    adapt_student_timetable,
    compute_topic_priority_rationale,
    generate_assistant_reply,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")

VALID_PRIORITIES = {"High", "Medium", "Low"}
VALID_TOPIC_STATUSES = {"pending", "in_progress", "completed"}
VALID_SCHEDULE_STATUSES = {"scheduled", "completed", "missed", "rescheduled"}


# ============================================================================
# 1. Dashboard Overview API
# ============================================================================
@api_bp.route("/dashboard", methods=["GET"])
@login_required_api
def get_dashboard(student):
    today = date.today()
    sid = student.student_id

    subjects = Subject.query.filter_by(student_id=sid).all()
    topics_analysis = analyze_student_topics(sid)
    topics = topics_analysis["topics"]
    weak_count = topics_analysis["summary"]["weak"]

    completed_topics = sum(1 for t in topics if t["status"] == "completed")
    pending_topics = len(topics) - completed_topics
    completion_rate = round((completed_topics / len(topics)) * 100) if topics else 0

    all_logs = StudyProgress.query.filter_by(student_id=sid).all()
    total_hours = round(sum(l.hours_studied for l in all_logs), 1)

    week_start = today - timedelta(days=6)
    weekly_logs = [l for l in all_logs if l.study_date >= week_start]
    weekly_hours = round(sum(l.hours_studied for l in weekly_logs), 1)
    hours_today = round(sum(l.hours_studied for l in all_logs if l.study_date == today), 1)

    # 7-day weekly bar chart series
    day_totals: dict[date, float] = {}
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        day_totals[d] = 0.0
    for l in weekly_logs:
        if l.study_date in day_totals:
            day_totals[l.study_date] += float(l.hours_studied)

    weekly_chart = {
        "labels": [d.strftime("%a %d") for d in day_totals.keys()],
        "hours": [round(v, 2) for v in day_totals.values()],
    }

    today_schedule = [
        s.to_dict()
        for s in StudySchedule.query.filter_by(student_id=sid, study_date=today)
        .order_by(StudySchedule.start_time.asc())
        .all()
    ]

    refresh_exam_preparedness(sid)
    upcoming_exams = [
        e.to_dict()
        for e in Exam.query.filter(Exam.student_id == sid, Exam.exam_date >= today)
        .order_by(Exam.exam_date.asc())
        .limit(5)
        .all()
    ]

    # Personalized AI suggestions
    revisions = get_revision_recommendations(sid, limit=3)
    suggestions = []

    if upcoming_exams and upcoming_exams[0]["days_left"] <= 7:
        ex = upcoming_exams[0]
        suggestions.append(
            {
                "category": "Exam Crunch",
                "severity": "high",
                "title": f"{ex['subject_name']} ({ex['exam_title']}) in {ex['days_left']} day(s)",
                "description": f"Current readiness is {ex['preparedness_score']}%. Prioritize practice sessions and exam prep blocks in your AI Planner.",
                "action_url": "/planner",
                "action_label": "Adjust Timetable",
            }
        )

    weak_list = [t for t in topics if t["weakness_level"] == "weak"]
    if weak_list:
        w = weak_list[0]
        suggestions.append(
            {
                "category": "Weak Topic Detector",
                "severity": "high",
                "title": f"Focus on {w['topic_name']} ({w['subject_name']})",
                "description": f"Weakness score {w['weakness_score']}/100 (Rating {w['understanding_rating']}/5). Take a diagnostic quiz or schedule a targeted revision slot.",
                "action_url": "/weak-topics",
                "action_label": "Review Topic",
            }
        )

    if revisions:
        r = revisions[0]
        suggestions.append(
            {
                "category": "Smart Revision Predictor",
                "severity": "medium",
                "title": f"Revise {r['topic_name']} on {r['recommended_date']}",
                "description": f"{r['reason']}. Spaced recall prevents forgetting before exams.",
                "action_url": "/weak-topics",
                "action_label": "Schedule Revision",
            }
        )

    missed_count = StudySchedule.query.filter_by(student_id=sid, status="missed").count()
    if missed_count > 0:
        suggestions.append(
            {
                "category": "Adaptive Planner",
                "severity": "medium",
                "title": f"{missed_count} missed study block(s) waiting to be rescheduled",
                "description": "Use Adaptive Rescheduling to automatically redistribute missed topics into upcoming open slots.",
                "action_url": "/planner",
                "action_label": "Adapt Now",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "category": "AI Coach",
                "severity": "low",
                "title": "You're right on schedule!",
                "description": "Keep logging daily sessions and ask the AI Study Assistant for active-recall practice questions.",
                "action_url": "/assistant",
                "action_label": "Open AI Assistant",
            }
        )

    headline = (
        f"Prioritize {upcoming_exams[0]['subject_name']} ({upcoming_exams[0]['days_left']}d to exam)"
        if upcoming_exams
        else f"Ready to tackle {pending_topics} pending topic(s) across {len(subjects)} subjects"
    )
    subtext = (
        f"You've logged {hours_today}h today toward your {student.daily_study_goal_hours}h goal. "
        f"{weak_count} weak topic(s) are flagged for boosted revision."
    )

    return jsonify(
        {
            "kpis": {
                "total_subjects": len(subjects),
                "total_study_hours": total_hours,
                "weekly_study_hours": weekly_hours,
                "completed_topics": completed_topics,
                "pending_topics": pending_topics,
                "completion_rate": completion_rate,
                "weak_topics_count": weak_count,
                "upcoming_exams_count": len(upcoming_exams),
            },
            "briefing": {"headline": headline, "subtext": subtext},
            "daily_progress": {
                "hours_today": hours_today,
                "goal_hours": student.daily_study_goal_hours,
            },
            "today_schedule": today_schedule,
            "weekly_chart": weekly_chart,
            "upcoming_exams": upcoming_exams,
            "ai_suggestions": suggestions,
        }
    )


# ============================================================================
# 2. Subjects, Topics & Exams CRUD APIs
# ============================================================================
@api_bp.route("/subjects", methods=["GET"])
@login_required_api
def list_subjects(student):
    subjects = Subject.query.filter_by(student_id=student.student_id).order_by(Subject.created_at.desc()).all()
    return jsonify({"subjects": [s.to_dict(include_children=True) for s in subjects]})


@api_bp.route("/subjects", methods=["POST"])
@login_required_api
def create_subject(student):
    data = request.get_json(silent=True) or {}
    name = (data.get("subject_name") or "").strip()
    if not name:
        return jsonify({"error": "Subject name is required."}), 400

    priority = data.get("priority", "Medium")
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": "Priority must be High, Medium, or Low."}), 400

    try:
        difficulty = int(data.get("difficulty_level", 3))
        target_hours = float(data.get("target_hours_per_week", 6.0))
    except (TypeError, ValueError):
        return jsonify({"error": "Difficulty and target hours must be valid numbers."}), 400

    if not 1 <= difficulty <= 5 or target_hours <= 0:
        return jsonify({"error": "Difficulty must be 1-5 and target hours > 0."}), 400

    subj = Subject(
        student_id=student.student_id,
        subject_name=name,
        subject_code=(data.get("subject_code") or "").strip()[:30] or None,
        difficulty_level=difficulty,
        priority=priority,
        color_tag=(data.get("color_tag") or "#6d28d9").strip()[:20],
        target_hours_per_week=target_hours,
    )
    db.session.add(subj)
    db.session.flush()

    exam_date_str = data.get("exam_date")
    if exam_date_str:
        try:
            ex_date = parse_date_str(exam_date_str)
        except ValueError:
            db.session.rollback()
            return jsonify({"error": "Invalid exam_date format (expected YYYY-MM-DD)."}), 400
        exam = Exam(
            student_id=student.student_id,
            subject_id=subj.subject_id,
            exam_title=(data.get("exam_title") or "Semester Exam").strip(),
            exam_date=ex_date,
        )
        db.session.add(exam)

    db.session.commit()
    sync_student_reminders(student)
    return jsonify({"subject": subj.to_dict(include_children=True)}), 201


@api_bp.route("/subjects/<int:subject_id>", methods=["PUT"])
@login_required_api
def update_subject(student, subject_id):
    subj = Subject.query.filter_by(subject_id=subject_id, student_id=student.student_id).first()
    if not subj:
        return jsonify({"error": "Subject not found."}), 404

    data = request.get_json(silent=True) or {}
    if "subject_name" in data:
        name = (data["subject_name"] or "").strip()
        if not name:
            return jsonify({"error": "Subject name cannot be empty."}), 400
        subj.subject_name = name
    if "subject_code" in data:
        subj.subject_code = (data["subject_code"] or "").strip()[:30] or None
    if "priority" in data:
        if data["priority"] not in VALID_PRIORITIES:
            return jsonify({"error": "Invalid priority."}), 400
        subj.priority = data["priority"]
    if "difficulty_level" in data:
        diff = int(data["difficulty_level"])
        if not 1 <= diff <= 5:
            return jsonify({"error": "Difficulty must be 1-5."}), 400
        subj.difficulty_level = diff
    if "target_hours_per_week" in data:
        hrs = float(data["target_hours_per_week"])
        if hrs <= 0:
            return jsonify({"error": "Target hours must be positive."}), 400
        subj.target_hours_per_week = hrs
    if "color_tag" in data:
        subj.color_tag = (data["color_tag"] or "#6d28d9").strip()[:20]

    exam_date_str = data.get("exam_date")
    if exam_date_str:
        try:
            ex_date = parse_date_str(exam_date_str)
        except ValueError:
            return jsonify({"error": "Invalid exam_date format."}), 400
        existing_exam = Exam.query.filter_by(student_id=student.student_id, subject_id=subj.subject_id).first()
        if existing_exam:
            existing_exam.exam_date = ex_date
            if data.get("exam_title"):
                existing_exam.exam_title = data["exam_title"].strip()
        else:
            db.session.add(
                Exam(
                    student_id=student.student_id,
                    subject_id=subj.subject_id,
                    exam_title=(data.get("exam_title") or "Semester Exam").strip(),
                    exam_date=ex_date,
                )
            )

    db.session.commit()
    sync_student_reminders(student)
    return jsonify({"subject": subj.to_dict(include_children=True)})


@api_bp.route("/subjects/<int:subject_id>", methods=["DELETE"])
@login_required_api
def delete_subject(student, subject_id):
    subj = Subject.query.filter_by(subject_id=subject_id, student_id=student.student_id).first()
    if not subj:
        return jsonify({"error": "Subject not found."}), 404
    db.session.delete(subj)
    db.session.commit()
    return jsonify({"message": "Subject deleted"})


@api_bp.route("/subjects/<int:subject_id>/topics", methods=["POST"])
@login_required_api
def create_topic(student, subject_id):
    subj = Subject.query.filter_by(subject_id=subject_id, student_id=student.student_id).first()
    if not subj:
        return jsonify({"error": "Subject not found."}), 404

    data = request.get_json(silent=True) or {}
    chapter = (data.get("chapter_name") or "").strip()
    topic_name = (data.get("topic_name") or "").strip()
    if not chapter or not topic_name:
        return jsonify({"error": "Chapter name and topic name are required."}), 400

    status = data.get("status", "pending")
    if status not in VALID_TOPIC_STATUSES:
        return jsonify({"error": "Invalid topic status."}), 400

    try:
        est_hours = float(data.get("estimated_hours", 2.0))
        rating = int(data.get("understanding_rating", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "Estimated hours and understanding rating must be numeric."}), 400

    if est_hours <= 0 or not 1 <= rating <= 5:
        return jsonify({"error": "Estimated hours must be > 0 and rating 1-5."}), 400

    topic = Topic(
        subject_id=subj.subject_id,
        student_id=student.student_id,
        chapter_name=chapter,
        topic_name=topic_name,
        estimated_hours=est_hours,
        status=status,
        understanding_rating=rating,
        last_studied_at=date.today() if status == "completed" else None,
    )
    db.session.add(topic)
    db.session.flush()
    refresh_topic_weakness(topic)
    db.session.commit()
    refresh_exam_preparedness(student.student_id)
    return jsonify({"topic": topic.to_dict()}), 201


@api_bp.route("/topics/<int:topic_id>", methods=["PUT"])
@login_required_api
def update_topic(student, topic_id):
    topic = Topic.query.filter_by(topic_id=topic_id, student_id=student.student_id).first()
    if not topic:
        return jsonify({"error": "Topic not found."}), 404

    data = request.get_json(silent=True) or {}
    if "chapter_name" in data:
        topic.chapter_name = (data["chapter_name"] or "").strip() or topic.chapter_name
    if "topic_name" in data:
        topic.topic_name = (data["topic_name"] or "").strip() or topic.topic_name
    if "estimated_hours" in data:
        hrs = float(data["estimated_hours"])
        if hrs <= 0:
            return jsonify({"error": "Estimated hours must be positive."}), 400
        topic.estimated_hours = hrs
    if "status" in data:
        if data["status"] not in VALID_TOPIC_STATUSES:
            return jsonify({"error": "Invalid topic status."}), 400
        topic.status = data["status"]
        if data["status"] == "completed":
            topic.last_studied_at = date.today()
    if "understanding_rating" in data:
        rating = int(data["understanding_rating"])
        if not 1 <= rating <= 5:
            return jsonify({"error": "Rating must be between 1 and 5."}), 400
        topic.understanding_rating = rating

    refresh_topic_weakness(topic)
    db.session.commit()
    refresh_exam_preparedness(student.student_id)
    return jsonify({"topic": topic.to_dict()})


@api_bp.route("/topics/<int:topic_id>/rating", methods=["PATCH"])
@login_required_api
def rate_topic(student, topic_id):
    topic = Topic.query.filter_by(topic_id=topic_id, student_id=student.student_id).first()
    if not topic:
        return jsonify({"error": "Topic not found."}), 404

    data = request.get_json(silent=True) or {}
    try:
        rating = int(data.get("understanding_rating"))
    except (TypeError, ValueError):
        return jsonify({"error": "Understanding rating must be an integer 1-5."}), 400

    if not 1 <= rating <= 5:
        return jsonify({"error": "Understanding rating must be between 1 and 5."}), 400

    topic.understanding_rating = rating
    metrics = refresh_topic_weakness(topic)
    db.session.commit()
    refresh_exam_preparedness(student.student_id)
    return jsonify({"topic": topic.to_dict(), "metrics": metrics})


@api_bp.route("/topics/<int:topic_id>", methods=["DELETE"])
@login_required_api
def delete_topic(student, topic_id):
    topic = Topic.query.filter_by(topic_id=topic_id, student_id=student.student_id).first()
    if not topic:
        return jsonify({"error": "Topic not found."}), 404
    db.session.delete(topic)
    db.session.commit()
    return jsonify({"message": "Topic deleted"})


@api_bp.route("/exams", methods=["POST"])
@login_required_api
def create_exam(student):
    data = request.get_json(silent=True) or {}
    subject_id = data.get("subject_id")
    subj = Subject.query.filter_by(subject_id=subject_id, student_id=student.student_id).first()
    if not subj:
        return jsonify({"error": "Valid subject_id is required."}), 404

    title = (data.get("exam_title") or "").strip()
    if not title:
        return jsonify({"error": "Exam title is required."}), 400

    try:
        exam_date = parse_date_str(data.get("exam_date"))
        if not exam_date:
            raise ValueError("Missing date")
    except ValueError:
        return jsonify({"error": "Valid exam_date (YYYY-MM-DD) is required."}), 400

    exam = Exam(
        student_id=student.student_id,
        subject_id=subj.subject_id,
        exam_title=title,
        exam_date=exam_date,
        exam_time=(data.get("exam_time") or "09:00").strip()[:15],
        syllabus_notes=(data.get("syllabus_notes") or "").strip()[:255] or None,
    )
    db.session.add(exam)
    db.session.commit()
    refresh_exam_preparedness(student.student_id)
    sync_student_reminders(student)
    return jsonify({"exam": exam.to_dict()}), 201


@api_bp.route("/exams/<int:exam_id>", methods=["DELETE"])
@login_required_api
def delete_exam(student, exam_id):
    exam = Exam.query.filter_by(exam_id=exam_id, student_id=student.student_id).first()
    if not exam:
        return jsonify({"error": "Exam not found."}), 404
    db.session.delete(exam)
    db.session.commit()
    return jsonify({"message": "Exam deleted"})


# ============================================================================
# 3. AI Study Planner & Schedule APIs
# ============================================================================
@api_bp.route("/planner/schedule", methods=["GET"])
@login_required_api
def get_schedule(student):
    today = date.today()
    rows = (
        StudySchedule.query.filter(
            StudySchedule.student_id == student.student_id,
            StudySchedule.study_date >= today - timedelta(days=1),
        )
        .order_by(StudySchedule.study_date.asc(), StudySchedule.start_time.asc())
        .all()
    )
    rationale = compute_topic_priority_rationale(student.student_id)
    return jsonify({"schedules": [r.to_dict() for r in rows], "rationale": rationale})


@api_bp.route("/planner/generate", methods=["POST"])
@login_required_api
def generate_timetable(student):
    data = request.get_json(silent=True) or {}
    try:
        weekday_hours = float(data.get("weekday_hours", student.daily_study_goal_hours or 4.0))
        weekend_hours = float(data.get("weekend_hours", 6.0))
        session_duration = float(data.get("session_duration", 1.5))
        days = int(data.get("days", 7))
    except (TypeError, ValueError):
        return jsonify({"error": "Numeric hours and duration values are required."}), 400

    preferred_time = data.get("preferred_time", student.preferred_study_time or "evening")
    focus_strategy = data.get("focus_strategy", "balanced")

    if preferred_time in {"morning", "afternoon", "evening"}:
        student.preferred_study_time = preferred_time
        student.daily_study_goal_hours = weekday_hours
        db.session.add(student)
        db.session.commit()

    result = generate_smart_timetable(
        student_id=student.student_id,
        weekday_hours=weekday_hours,
        weekend_hours=weekend_hours,
        preferred_time=preferred_time,
        focus_strategy=focus_strategy,
        session_duration=session_duration,
        days=max(1, min(14, days)),
    )
    if result["created_count"] == 0:
        return jsonify({"error": "Add at least one subject before generating a timetable."}), 400

    sync_student_reminders(student)
    return jsonify(
        {
            "message": f"Generated {result['created_count']} smart study blocks for the next {days} days!",
            **result,
        }
    )


@api_bp.route("/planner/adapt", methods=["POST"])
@login_required_api
def adapt_timetable_route(student):
    data = request.get_json(silent=True) or {}
    weekday_hours = float(data.get("weekday_hours", student.daily_study_goal_hours or 4.0))
    weekend_hours = float(data.get("weekend_hours", 6.0))
    preferred_time = data.get("preferred_time", student.preferred_study_time or "evening")

    result = adapt_student_timetable(
        student_id=student.student_id,
        weekday_hours=weekday_hours,
        weekend_hours=weekend_hours,
        preferred_time=preferred_time,
    )
    if result["created_count"] == 0:
        return jsonify({"error": "Add subjects first to adapt your timetable."}), 400

    return jsonify(
        {
            "message": f"Timetable adapted! Rebalanced {result['rescheduled_missed_count']} missed session(s) across {result['created_count']} upcoming blocks.",
            **result,
        }
    )


@api_bp.route("/planner/revision-slot", methods=["POST"])
@login_required_api
def schedule_revision_slot(student):
    data = request.get_json(silent=True) or {}
    topic_id = data.get("topic_id")
    topic = Topic.query.filter_by(topic_id=topic_id, student_id=student.student_id).first()
    if not topic:
        return jsonify({"error": "Topic not found."}), 404

    target_date = parse_date_str(data.get("study_date")) or date.today()
    existing_count = StudySchedule.query.filter_by(
        student_id=student.student_id, study_date=target_date
    ).count()
    start_hour = min(21, 18 + existing_count)
    slot = StudySchedule(
        student_id=student.student_id,
        subject_id=topic.subject_id,
        topic_id=topic.topic_id,
        study_date=target_date,
        start_time=f"{start_hour:02d}:00",
        end_time=f"{start_hour + 1:02d}:00",
        duration_hours=1.0,
        session_type="revision",
        priority_score=85.0,
        is_ai_generated=True,
        status="scheduled",
        notes="Smart Revision Predictor slot",
    )
    db.session.add(slot)
    db.session.commit()
    return jsonify({"message": f"Revision slot scheduled for {target_date.isoformat()}.", "schedule": slot.to_dict()}), 201


@api_bp.route("/schedules/<int:schedule_id>/status", methods=["PATCH"])
@login_required_api
def update_schedule_status(student, schedule_id):
    slot = StudySchedule.query.filter_by(schedule_id=schedule_id, student_id=student.student_id).first()
    if not slot:
        return jsonify({"error": "Schedule slot not found."}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in VALID_SCHEDULE_STATUSES:
        return jsonify({"error": "Invalid schedule status."}), 400

    prev_status = slot.status
    slot.status = new_status
    db.session.add(slot)

    # Automatically log StudyProgress & update topic metadata on completion
    if new_status == "completed" and prev_status != "completed":
        progress = StudyProgress(
            student_id=student.student_id,
            subject_id=slot.subject_id,
            topic_id=slot.topic_id,
            study_date=date.today(),
            hours_studied=slot.duration_hours,
            topics_completed_count=1 if slot.topic_id else 0,
            focus_rating=4,
            notes=f"Completed planned {slot.session_type} block",
        )
        db.session.add(progress)
        if slot.topic:
            slot.topic.last_studied_at = date.today()
            if slot.session_type == "revision":
                slot.topic.revision_count += 1
            elif slot.topic.status == "pending":
                slot.topic.status = "completed"
            refresh_topic_weakness(slot.topic)

    db.session.commit()
    refresh_exam_preparedness(student.student_id)
    return jsonify({"schedule": slot.to_dict()})


# ============================================================================
# 4. Weak Topics, Quizzes & Revision Predictor APIs
# ============================================================================
@api_bp.route("/weak-topics", methods=["GET"])
@login_required_api
def get_weak_topics(student):
    analysis = analyze_student_topics(student.student_id)
    revisions = get_revision_recommendations(student.student_id, limit=8)
    return jsonify({**analysis, "revision_recommendations": revisions})


@api_bp.route("/quizzes", methods=["POST"])
@login_required_api
def record_quiz_result(student):
    data = request.get_json(silent=True) or {}
    topic = Topic.query.filter_by(topic_id=data.get("topic_id"), student_id=student.student_id).first()
    if not topic:
        return jsonify({"error": "Topic not found."}), 404

    title = (data.get("quiz_title") or "Topic Quiz").strip()
    try:
        score = float(data.get("score"))
        max_score = float(data.get("max_score", 10.0))
    except (TypeError, ValueError):
        return jsonify({"error": "Score and max_score must be valid numbers."}), 400

    if max_score <= 0 or score < 0 or score > max_score:
        return jsonify({"error": "Score must be between 0 and max_score."}), 400

    pct = round((score / max_score) * 100.0, 1)
    quiz = QuizResult(
        student_id=student.student_id,
        subject_id=topic.subject_id,
        topic_id=topic.topic_id,
        quiz_title=title,
        score=score,
        max_score=max_score,
        percentage=pct,
        difficulty_feedback=(data.get("difficulty_feedback") or "Medium").strip()[:40],
    )
    db.session.add(quiz)
    topic.last_studied_at = date.today()
    db.session.flush()
    metrics = refresh_topic_weakness(topic)
    db.session.commit()
    refresh_exam_preparedness(student.student_id)
    sync_student_reminders(student)
    return jsonify({"quiz": quiz.to_dict(), "topic_metrics": metrics}), 201


# ============================================================================
# 5. Progress Tracking & Analytics APIs
# ============================================================================
@api_bp.route("/progress", methods=["POST"])
@login_required_api
def log_study_progress(student):
    data = request.get_json(silent=True) or {}
    subj = Subject.query.filter_by(subject_id=data.get("subject_id"), student_id=student.student_id).first()
    if not subj:
        return jsonify({"error": "Subject not found."}), 404

    topic_id = data.get("topic_id")
    topic = None
    if topic_id:
        topic = Topic.query.filter_by(topic_id=topic_id, student_id=student.student_id).first()
        if not topic:
            return jsonify({"error": "Topic not found."}), 404

    try:
        hours = float(data.get("hours_studied"))
        focus = int(data.get("focus_rating", 4))
    except (TypeError, ValueError):
        return jsonify({"error": "Hours studied and focus rating must be numeric."}), 400

    if hours <= 0 or hours > 20 or not 1 <= focus <= 5:
        return jsonify({"error": "Hours must be 0.1-20 and focus rating 1-5."}), 400

    study_date = parse_date_str(data.get("study_date")) or date.today()

    entry = StudyProgress(
        student_id=student.student_id,
        subject_id=subj.subject_id,
        topic_id=topic.topic_id if topic else None,
        study_date=study_date,
        hours_studied=hours,
        topics_completed_count=1 if topic and topic.status == "completed" else 0,
        focus_rating=focus,
        notes=(data.get("notes") or "").strip()[:255] or None,
    )
    db.session.add(entry)
    if topic:
        topic.last_studied_at = study_date
        if topic.status == "pending":
            topic.status = "in_progress"
        refresh_topic_weakness(topic)

    db.session.commit()
    sync_student_reminders(student)
    return jsonify({"progress": entry.to_dict()}), 201


@api_bp.route("/progress/analytics", methods=["GET"])
@login_required_api
def get_progress_analytics(student):
    sid = student.student_id
    today = date.today()
    logs = StudyProgress.query.filter_by(student_id=sid).order_by(StudyProgress.study_date.desc()).all()
    subjects = Subject.query.filter_by(student_id=sid).all()
    topics = Topic.query.filter_by(student_id=sid).all()

    today_hours = sum(l.hours_studied for l in logs if l.study_date == today)
    week_start = today - timedelta(days=6)
    weekly_hours = sum(l.hours_studied for l in logs if l.study_date >= week_start)

    # Weekly series
    weekly_map = {today - timedelta(days=offset): 0.0 for offset in range(6, -1, -1)}
    for l in logs:
        if l.study_date in weekly_map:
            weekly_map[l.study_date] += float(l.hours_studied)

    # 14-day consistency & streak
    days_14 = {today - timedelta(days=offset): 0.0 for offset in range(13, -1, -1)}
    all_dates_with_study = set()
    for l in logs:
        if l.hours_studied > 0:
            all_dates_with_study.add(l.study_date)
        if l.study_date in days_14:
            days_14[l.study_date] += float(l.hours_studied)

    streak = 0
    cursor = today
    while cursor in all_dates_with_study:
        streak += 1
        cursor -= timedelta(days=1)

    active_14 = sum(1 for v in days_14.values() if v > 0)
    consistency_pct = round((active_14 / 14.0) * 100)

    # Chapters calculation
    chapters_map: dict[tuple[int, str], list[Topic]] = {}
    for t in topics:
        key = (t.subject_id, t.chapter_name)
        chapters_map.setdefault(key, []).append(t)
    completed_chapters = sum(
        1 for ch_topics in chapters_map.values() if all(t.status == "completed" for t in ch_topics)
    )
    completed_topics = sum(1 for t in topics if t.status == "completed")

    # Subject-wise progress
    subject_progress = []
    for s in subjects:
        s_topics = [t for t in topics if t.subject_id == s.subject_id]
        s_done = sum(1 for t in s_topics if t.status == "completed")
        s_hours = round(sum(l.hours_studied for l in logs if l.subject_id == s.subject_id), 1)
        pct = round((s_done / len(s_topics)) * 100) if s_topics else 0
        subject_progress.append(
            {
                "subject_id": s.subject_id,
                "subject_name": s.subject_name,
                "color_tag": s.color_tag,
                "total_topics": len(s_topics),
                "completed_topics": s_done,
                "completion_pct": pct,
                "hours_studied": s_hours,
            }
        )

    return jsonify(
        {
            "summary": {
                "today_hours": round(today_hours, 1),
                "daily_goal_hours": student.daily_study_goal_hours,
                "weekly_hours": round(weekly_hours, 1),
                "streak_days": streak,
                "consistency_pct": consistency_pct,
                "completed_chapters": completed_chapters,
                "total_chapters": len(chapters_map),
                "completed_topics": completed_topics,
                "total_topics": len(topics),
            },
            "weekly_chart": {
                "labels": [d.strftime("%a %d") for d in weekly_map.keys()],
                "hours": [round(v, 1) for v in weekly_map.values()],
            },
            "subject_progress": subject_progress,
            "consistency_14d": [
                {"date": d.isoformat(), "label": d.strftime("%d"), "hours": round(v, 1)}
                for d, v in days_14.items()
            ],
            "recent_logs": [l.to_dict() for l in logs[:10]],
        }
    )


# ============================================================================
# 6. Reminders & AI Study Assistant APIs
# ============================================================================
@api_bp.route("/reminders", methods=["GET"])
@login_required_api
def list_reminders(student):
    query = Reminder.query.filter_by(student_id=student.student_id)
    if request.args.get("only_pending") == "1":
        query = query.filter_by(is_completed=False)
    reminders = query.order_by(Reminder.is_completed.asc(), Reminder.due_date.asc()).all()
    return jsonify({"reminders": [r.to_dict() for r in reminders]})


@api_bp.route("/reminders/sync", methods=["POST"])
@login_required_api
def sync_reminders_route(student):
    count = sync_student_reminders(student)
    return jsonify({"message": f"Refreshed {count} smart study & exam reminder(s).", "synced": count})


@api_bp.route("/reminders", methods=["POST"])
@login_required_api
def create_custom_reminder(student):
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    message = (data.get("message") or "").strip()
    if not title or not message:
        return jsonify({"error": "Title and message are required."}), 400

    try:
        due = parse_date_str(data.get("due_date")) or date.today()
    except ValueError:
        return jsonify({"error": "Invalid due_date format."}), 400

    priority = data.get("priority", "medium")
    if priority not in {"high", "medium", "low"}:
        priority = "medium"

    rem = Reminder(
        student_id=student.student_id,
        reminder_type="custom",
        title=title,
        message=message,
        due_date=due,
        priority=priority,
        is_auto_generated=False,
    )
    db.session.add(rem)
    db.session.commit()
    return jsonify({"reminder": rem.to_dict()}), 201


@api_bp.route("/reminders/<int:reminder_id>", methods=["PATCH"])
@login_required_api
def update_reminder(student, reminder_id):
    rem = Reminder.query.filter_by(reminder_id=reminder_id, student_id=student.student_id).first()
    if not rem:
        return jsonify({"error": "Reminder not found."}), 404
    data = request.get_json(silent=True) or {}
    if "is_completed" in data:
        rem.is_completed = bool(data["is_completed"])
    if "is_read" in data:
        rem.is_read = bool(data["is_read"])
    db.session.commit()
    return jsonify({"reminder": rem.to_dict()})


@api_bp.route("/reminders/<int:reminder_id>", methods=["DELETE"])
@login_required_api
def delete_reminder(student, reminder_id):
    rem = Reminder.query.filter_by(reminder_id=reminder_id, student_id=student.student_id).first()
    if not rem:
        return jsonify({"error": "Reminder not found."}), 404
    db.session.delete(rem)
    db.session.commit()
    return jsonify({"message": "Reminder deleted"})


@api_bp.route("/assistant/chat", methods=["POST"])
@login_required_api
def assistant_chat(student):
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400
    response = generate_assistant_reply(student.student_id, message)
    return jsonify(response)

