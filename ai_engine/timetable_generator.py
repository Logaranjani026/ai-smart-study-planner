from datetime import date, datetime, timedelta
from models import db, Subject, Topic, Exam, StudySchedule
from ai_engine.weak_topic_detector import compute_topic_weakness
from ai_engine.revision_predictor import predict_topic_next_revision


START_HOUR_MAP = {
    "morning": (7, 0),
    "afternoon": (14, 0),
    "evening": (18, 0),
}

PRIORITY_POINTS = {"High": 22.0, "Medium": 12.0, "Low": 4.0}
WEAKNESS_POINTS = {"weak": 24.0, "average": 11.0, "strong": 2.0}


def _format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def _score_candidate(
    topic: Topic,
    subject: Subject,
    earliest_exam: date | None,
    strategy: str = "balanced",
) -> tuple[float, str, str]:
    """
    Compute AI priority score, session type, and human-readable rationale.
    """
    today = date.today()
    weakness = compute_topic_weakness(topic, subject=subject)
    w_level = weakness["weakness_level"]

    exam_boost = 0.0
    exam_note = ""
    if earliest_exam:
        days_left = (earliest_exam - today).days
        if days_left <= 3:
            exam_boost = 44.0
            exam_note = f"Exam in {max(0, days_left)}d"
        elif days_left <= 7:
            exam_boost = 32.0
            exam_note = f"Exam in {days_left}d"
        elif days_left <= 14:
            exam_boost = 20.0
            exam_note = f"Exam in {days_left}d"
        elif days_left <= 30:
            exam_boost = 10.0
            exam_note = f"Exam in {days_left}d"

    prio_pts = PRIORITY_POINTS.get(subject.priority, 10.0)
    diff_pts = (subject.difficulty_level or 3) * 3.2
    weak_pts = WEAKNESS_POINTS.get(w_level, 10.0)

    if strategy == "exam_crunch":
        exam_boost *= 1.45
    elif strategy == "weak_first":
        weak_pts *= 1.55

    score = round(exam_boost + prio_pts + diff_pts + weak_pts, 1)

    if topic.status == "completed":
        session_type = "revision"
    elif earliest_exam and (earliest_exam - today).days <= 5:
        session_type = "exam_prep"
    elif w_level == "weak":
        session_type = "revision" if topic.revision_count > 0 else "learning"
    else:
        session_type = "learning"

    reasons = [f"{subject.priority} priority", f"Difficulty {subject.difficulty_level}/5", f"{w_level.title()} topic"]
    if exam_note:
        reasons.insert(0, exam_note)

    return score, session_type, " · ".join(reasons)


def compute_topic_priority_rationale(student_id: int, limit: int = 6) -> list[dict]:
    today = date.today()
    subjects = {s.subject_id: s for s in Subject.query.filter_by(student_id=student_id).all()}
    topics = Topic.query.filter_by(student_id=student_id).all()
    exams = Exam.query.filter(Exam.student_id == student_id, Exam.exam_date >= today).all()

    earliest_exam_map: dict[int, date] = {}
    for ex in exams:
        cur = earliest_exam_map.get(ex.subject_id)
        if cur is None or ex.exam_date < cur:
            earliest_exam_map[ex.subject_id] = ex.exam_date

    items = []
    for t in topics:
        subj = subjects.get(t.subject_id)
        if not subj:
            continue
        score, _, reason = _score_candidate(t, subj, earliest_exam_map.get(subj.subject_id))
        items.append({"topic_name": t.topic_name, "priority_score": score, "reason": reason})

    items.sort(key=lambda x: x["priority_score"], reverse=True)
    return items[:limit]


def generate_smart_timetable(
    student_id: int,
    weekday_hours: float = 4.0,
    weekend_hours: float = 6.0,
    preferred_time: str = "evening",
    focus_strategy: str = "balanced",
    session_duration: float = 1.5,
    days: int = 7,
    start_date: date | None = None,
) -> dict:
    """
    AI Smart Timetable Generator:
    Allocates personalized daily and weekly study blocks based on available hours,
    subject difficulty, priority, exam proximity, and topic completion/weakness.
    """
    today = start_date or date.today()
    end_window = today + timedelta(days=days - 1)

    subjects = Subject.query.filter_by(student_id=student_id).all()
    if not subjects:
        return {"created_count": 0, "schedules": [], "rationale": []}

    subject_map = {s.subject_id: s for s in subjects}
    topics = Topic.query.filter_by(student_id=student_id).all()
    exams = Exam.query.filter(Exam.student_id == student_id, Exam.exam_date >= today).all()

    earliest_exam_map: dict[int, date] = {}
    for ex in exams:
        cur = earliest_exam_map.get(ex.subject_id)
        if cur is None or ex.exam_date < cur:
            earliest_exam_map[ex.subject_id] = ex.exam_date

    # Preserve completed sessions, clear future non-completed AI sessions in window
    StudySchedule.query.filter(
        StudySchedule.student_id == student_id,
        StudySchedule.study_date >= today,
        StudySchedule.study_date <= end_window,
        StudySchedule.status != "completed",
    ).delete(synchronize_session=False)

    # Build weighted queue of topics (pending/in_progress + due revisions)
    candidates = []
    for t in topics:
        subj = subject_map.get(t.subject_id)
        if not subj:
            continue
        earliest_exam = earliest_exam_map.get(subj.subject_id)
        score, session_type, reason = _score_candidate(t, subj, earliest_exam, strategy=focus_strategy)

        if t.status == "completed":
            rec_date, _ = predict_topic_next_revision(t, earliest_exam_date=earliest_exam, reference_date=today)
            if rec_date > end_window:
                continue
            needed_hours = min(1.0, float(session_duration))
            reason = f"Due spaced revision ({t.weakness_level})"
        else:
            needed_hours = max(0.75, float(t.estimated_hours or 1.5))

        candidates.append(
            {
                "topic": t,
                "subject": subj,
                "score": score,
                "session_type": session_type,
                "reason": reason,
                "remaining_hours": needed_hours,
            }
        )

    # If student added subjects without topics yet, create subject-level study blocks
    if not candidates:
        for subj in subjects:
            candidates.append(
                {
                    "topic": None,
                    "subject": subj,
                    "score": PRIORITY_POINTS.get(subj.priority, 10.0) + (subj.difficulty_level * 4),
                    "session_type": "learning",
                    "reason": f"{subj.priority} priority subject block",
                    "remaining_hours": float(subj.target_hours_per_week or 4.0),
                }
            )

    candidates.sort(key=lambda c: c["score"], reverse=True)

    # Check existing completed hours per day so we don't overbook
    completed_existing = StudySchedule.query.filter(
        StudySchedule.student_id == student_id,
        StudySchedule.study_date >= today,
        StudySchedule.study_date <= end_window,
        StudySchedule.status == "completed",
    ).all()
    completed_hrs_by_day: dict[date, float] = {}
    for row in completed_existing:
        completed_hrs_by_day[row.study_date] = completed_hrs_by_day.get(row.study_date, 0.0) + float(row.duration_hours)

    start_h, start_m = START_HOUR_MAP.get(preferred_time, (18, 0))
    created_rows = []
    block_dur = max(0.5, min(3.0, float(session_duration)))

    for day_offset in range(days):
        cur_date = today + timedelta(days=day_offset)
        is_weekend = cur_date.weekday() >= 5
        daily_budget = float(weekend_hours if is_weekend else weekday_hours)
        used_hours = completed_hrs_by_day.get(cur_date, 0.0)
        cursor_dt = datetime.combine(cur_date, datetime.min.time()).replace(hour=start_h, minute=start_m)
        if used_hours > 0:
            cursor_dt += timedelta(minutes=int(used_hours * 60) + 15)

        subjects_used_today: set[int] = set()

        while used_hours + 0.5 <= daily_budget:
            # Prefer a candidate not yet studied today for balanced cognitive variety
            pick = None
            for c in candidates:
                if c["remaining_hours"] > 0 and c["subject"].subject_id not in subjects_used_today:
                    pick = c
                    break
            if pick is None:
                for c in candidates:
                    if c["remaining_hours"] > 0:
                        pick = c
                        break
            if pick is None:
                # Cycle top candidates for extra practice/revision if weekly hours remain
                top = candidates[len(created_rows) % len(candidates)]
                top["remaining_hours"] = block_dur
                pick = top

            alloc = min(block_dur, daily_budget - used_hours, max(0.5, pick["remaining_hours"]))
            alloc = round(alloc * 2) / 2  # nearest 0.5 hr
            if alloc < 0.5:
                break

            slot_end = cursor_dt + timedelta(minutes=int(alloc * 60))
            row = StudySchedule(
                student_id=student_id,
                subject_id=pick["subject"].subject_id,
                topic_id=pick["topic"].topic_id if pick["topic"] else None,
                study_date=cur_date,
                start_time=_format_time(cursor_dt),
                end_time=_format_time(slot_end),
                duration_hours=alloc,
                session_type=pick["session_type"],
                priority_score=pick["score"],
                is_ai_generated=True,
                status="scheduled",
                notes=pick["reason"],
            )
            db.session.add(row)
            created_rows.append(row)

            pick["remaining_hours"] = max(0.0, pick["remaining_hours"] - alloc)
            used_hours += alloc
            subjects_used_today.add(pick["subject"].subject_id)
            cursor_dt = slot_end + timedelta(minutes=15)

    db.session.commit()
    rationale = [
        {
            "topic_name": c["topic"].topic_name if c["topic"] else c["subject"].subject_name,
            "priority_score": c["score"],
            "reason": c["reason"],
        }
        for c in candidates[:6]
    ]
    return {
        "created_count": len(created_rows),
        "schedules": [r.to_dict() for r in created_rows],
        "rationale": rationale,
    }


def adapt_student_timetable(
    student_id: int,
    weekday_hours: float = 4.0,
    weekend_hours: float = 6.0,
    preferred_time: str = "evening",
) -> dict:
    """
    Adaptive Study Planner:
    Detects missed or rescheduled blocks, marks missed items as rescheduled,
    boosts unfinished high-priority topics, and regenerates upcoming open days
    without altering completed sessions.
    """
    today = date.today()
    missed_rows = StudySchedule.query.filter(
        StudySchedule.student_id == student_id,
        StudySchedule.status == "missed",
    ).all()

    rescheduled_count = len(missed_rows)
    for row in missed_rows:
        row.status = "rescheduled"
        db.session.add(row)
    db.session.commit()

    # Re-balance starting today (or tomorrow if today already has completed slots)
    result = generate_smart_timetable(
        student_id=student_id,
        weekday_hours=weekday_hours,
        weekend_hours=weekend_hours,
        preferred_time=preferred_time,
        focus_strategy="weak_first" if rescheduled_count > 0 else "balanced",
        session_duration=1.5,
        days=7,
        start_date=today,
    )
    result["rescheduled_missed_count"] = rescheduled_count
    return result

