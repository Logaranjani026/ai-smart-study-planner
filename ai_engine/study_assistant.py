from datetime import date
from models import db, Student, Subject, Topic, Exam, StudyProgress, StudySchedule
from ai_engine.weak_topic_detector import analyze_student_topics
from ai_engine.revision_predictor import get_revision_recommendations


CONCEPT_LIBRARY = {
    "dynamic programming": (
        "**Dynamic Programming (DP)** breaks a complex problem into overlapping subproblems and stores intermediate results so each subproblem is solved only once.",
        [
            "Identify optimal substructure: write the recurrence relation first.",
            "Choose Memoization (top-down recursion + cache) or Tabulation (bottom-up DP table).",
            "Trace base cases on a small example (n = 0, 1, 2) before coding.",
        ],
        "Practice Problem: Try solving Coin Change or 0/1 Knapsack by writing the state transition dp[i][w] explicitly.",
    ),
    "normalization": (
        "**Database Normalization** eliminates redundancy and update anomalies by organizing tables around functional dependencies.",
        [
            "1NF: Atomic column values and no repeating groups.",
            "2NF: In 1NF and no partial dependency on a composite primary key.",
            "3NF: In 2NF and no transitive dependencies (non-key -> non-key).",
            "BCNF: Every determinant is a candidate key.",
        ],
        "Quick Check: Given R(A, B, C) with A->B and B->C, identify why R violates 3NF and decompose it.",
    ),
    "deadlock": (
        "**OS Deadlock** occurs when processes hold resources while waiting indefinitely for resources held by other waiting processes.",
        [
            "Four Coffman Conditions (all must hold): Mutual Exclusion, Hold & Wait, No Preemption, Circular Wait.",
            "Prevention breaks at least one condition (e.g., strict resource ordering prevents Circular Wait).",
            "Avoidance uses Banker's Algorithm to check safe states before granting requests.",
        ],
        "Quick Check: Explain why breaking Circular Wait is the most practical deadlock prevention rule.",
    ),
    "eigenvalues": (
        "**Eigenvalues and Eigenvectors** satisfy A*v = lambda*v, meaning matrix A only scales vector v without changing its direction.",
        [
            "Compute characteristic polynomial: det(A - lambda*I) = 0.",
            "Substitute each eigenvalue back into (A - lambda*I)v = 0 to find the eigenspace.",
            "Symmetric matrices always have real eigenvalues and orthogonal eigenvectors.",
        ],
        "Quick Check: Find the eigenvalues of [[2, 1], [1, 2]] by solving (2 - lambda)^2 - 1 = 0.",
    ),
    "graph": (
        "**Graph Algorithms (BFS, DFS, Dijkstra)** model networks of vertices and edges for traversal and shortest-path optimization.",
        [
            "BFS uses a Queue and guarantees shortest path in unweighted graphs.",
            "DFS uses a Stack/recursion and powers cycle detection and topological sorting.",
            "Dijkstra uses a Min-Heap priority queue for non-negative weighted shortest paths.",
        ],
        "Quick Check: Why does Dijkstra fail when edges have negative weights (hint: greedy relaxation)?",
    ),
    "indexing": (
        "**Database Indexing (B+ Trees & Hash Indexes)** accelerates SELECT queries by avoiding full table scans.",
        [
            "B+ Trees keep keys sorted in leaf nodes linked sequentially for fast range queries.",
            "Composite indexes follow the leftmost prefix rule.",
            "Balance read speed gains against extra INSERT/UPDATE write overhead.",
        ],
        "Quick Check: For index (student_id, study_date), why does filtering by study_date alone skip the index?",
    ),
}


def generate_assistant_reply(student_id: int, user_message: str) -> dict:
    """
    Context-aware AI Study Assistant grounded in the student's live MySQL records.
    """
    msg = (user_message or "").strip()
    lower = msg.lower()

    student = db.session.get(Student, student_id)
    subjects = Subject.query.filter_by(student_id=student_id).all()
    topics_analysis = analyze_student_topics(student_id)
    analyzed_topics = topics_analysis["topics"]
    weak_topics = [t for t in analyzed_topics if t["weakness_level"] == "weak"]
    revisions = get_revision_recommendations(student_id, limit=5)

    today = date.today()
    upcoming_exams = (
        Exam.query.filter(Exam.student_id == student_id, Exam.exam_date >= today)
        .order_by(Exam.exam_date.asc())
        .all()
    )
    today_schedules = StudySchedule.query.filter_by(student_id=student_id, study_date=today).all()
    total_hours = round(
        sum(p.hours_studied for p in StudyProgress.query.filter_by(student_id=student_id).all()), 1
    )

    first_name = student.full_name.split()[0] if student else "there"

    # 1. Check for specific concept / topic explanation request
    for keyword, (summary, steps, check_q) in CONCEPT_LIBRARY.items():
        if keyword in lower:
            bullets = "\n".join(f"- {step}" for step in steps)
            reply = (
                f"Here is a clear breakdown of **{keyword.title()}**, {first_name}:\n\n"
                f"{summary}\n\n"
                f"**Core Study Steps:**\n{bullets}\n\n"
                f"**{check_q}**"
            )
            return {
                "reply": reply,
                "suggestions": [
                    "What should I revise today?",
                    "Give me a 3-day prep plan for my next exam",
                ],
            }

    # 2. Explain weakest topic
    if "weak" in lower or "difficult" in lower or "struggl" in lower:
        if not weak_topics:
            reply = (
                f"Great news, {first_name} — you currently have **0 topics flagged as Weak**! "
                "Keep taking diagnostic quizzes on the Weak Topic Detector page to verify long-term mastery."
            )
        else:
            top = weak_topics[:3]
            lines = "\n".join(
                f"- **{t['topic_name']}** ({t['subject_name']}) — Weakness Score: {t['weakness_score']}/100, "
                f"Understanding: {t['understanding_rating']}/5"
                for t in top
            )
            focus = top[0]
            reply = (
                f"Based on your ratings and quiz results, these are your top priority weak topics:\n"
                f"{lines}\n\n"
                f"**Recommended 3-Step Fix for {focus['topic_name']}:**\n"
                f"- Spend 25 minutes writing a one-page summary from memory (Feynman technique).\n"
                f"- Work through 3 solved examples, then retry 2 unseen problems.\n"
                f"- Log a Quick Diagnostic Quiz afterwards to verify your score rises above 75%."
            )
        return {
            "reply": reply,
            "suggestions": [
                "Schedule revision for my weak topics",
                "Organize my timetable",
            ],
        }

    # 3. Revision recommendations
    if "revise" in lower or "revision" in lower or "forget" in lower:
        if not revisions:
            reply = (
                f"You don't have urgent overdue revisions right now, {first_name}. "
                "Focus on completing pending syllabus topics first so the Smart Revision Predictor can schedule spaced reviews."
            )
        else:
            lines = "\n".join(
                f"- **{r['topic_name']}** ({r['subject_name']}) — Recommended: **{r['recommended_date']}** ({r['reason']})"
                for r in revisions[:4]
            )
            reply = (
                f"**Smart Revision Predictor Queue for {first_name}:**\n"
                f"{lines}\n\n"
                "- Use 20-minute active recall blurting before reviewing notes for maximum retention."
            )
        return {
            "reply": reply,
            "suggestions": [
                "Explain my weakest topic",
                "How are my upcoming exams looking?",
            ],
        }

    # 4. Timetable / Schedule organization
    if "timetable" in lower or "schedule" in lower or "organize" in lower or "plan" in lower:
        planned_today = round(sum(s.duration_hours for s in today_schedules), 1)
        exam_line = (
            f"Your nearest exam is **{upcoming_exams[0].subject.subject_name} ({upcoming_exams[0].exam_title})** "
            f"in **{(upcoming_exams[0].exam_date - today).days} days**."
            if upcoming_exams
            else "You haven't added any upcoming exam dates yet."
        )
        reply = (
            f"Let's optimize your schedule, {first_name}:\n\n"
            f"- **Today's Plan:** {len(today_schedules)} blocks totaling **{planned_today} hrs** (Daily Goal: {student.daily_study_goal_hours} hrs).\n"
            f"- **Exam Horizon:** {exam_line}\n"
            f"- **Optimal Strategy:** Put your hardest or weakest topic first when mental energy peaks, followed by a 15-minute break and a spaced-revision block.\n"
            "- Open the **AI Study Planner** page and click **Generate AI Timetable** (or **Adapt Timetable** if you missed a block) to auto-balance the next 7 days."
        )
        return {
            "reply": reply,
            "suggestions": [
                "What topics should I revise today?",
                "Personalized study tips",
            ],
        }

    # 5. Personalized study tips / progress overview
    if "tip" in lower or "progress" in lower or "exam" in lower or "help" in lower:
        total_t = len(analyzed_topics)
        done_t = sum(1 for t in analyzed_topics if t["status"] == "completed")
        pct = round((done_t / total_t) * 100) if total_t else 0
        reply = (
            f"Here is your personalized study strategy snapshot, {first_name}:\n\n"
            f"- **Syllabus Mastery:** {done_t}/{total_t} topics completed ({pct}%) across {len(subjects)} subjects.\n"
            f"- **Total Study Logged:** {total_hours} hours.\n"
            f"- **Weak Topics to Watch:** {len(weak_topics)} topics flagged.\n\n"
            "**3 High-Impact Tips for This Week:**\n"
            "- Use 50-minute focused blocks with 10-minute breaks (Pomodoro / deep work).\n"
            "- Test yourself with a short quiz after every chapter instead of passive rereading.\n"
            "- Review upcoming exam subjects at least 48 hours ahead using active recall."
        )
        return {
            "reply": reply,
            "suggestions": [
                "Explain my weakest topic",
                "What should I revise today?",
            ],
        }

    # 6. Generic topic explanation fallback (Feynman guide for any topic mentioned)
    if "explain" in lower or "what is" in lower or "how does" in lower or "understand" in lower:
        cleaned = (
            msg.replace("Explain", "")
            .replace("explain", "")
            .replace("step by step", "")
            .strip(" :?.")
        ) or "this concept"
        reply = (
            f"Here is a structured study framework to master **{cleaned}**, {first_name}:\n\n"
            f"- **1. Core Intuition:** Summarize what problem *{cleaned}* solves in two plain-English sentences without jargon.\n"
            f"- **2. Key Building Blocks:** List the 3 essential rules, formulas, or mechanisms behind *{cleaned}*.\n"
            f"- **3. Worked Example:** Trace one concrete input/scenario step by step from start to output.\n"
            f"- **4. Exam Edge Cases:** Write down the top 2 mistakes students make on *{cleaned}* questions.\n\n"
            "Once you review these 4 steps, take a Quick Diagnostic Quiz in **Weak Topic Detector** to lock it in!"
        )
        return {
            "reply": reply,
            "suggestions": [
                "Explain Dynamic Programming",
                "Explain Database Normalization",
                "What should I revise today?",
            ],
        }

    # Default smart greeting / status summary
    reply = (
        f"I'm synced with your study workspace, {first_name}! You currently have **{len(subjects)} subjects**, "
        f"**{len(weak_topics)} weak topics**, and **{len(upcoming_exams)} upcoming exams**.\n\n"
        "- Ask me to **explain any topic** (e.g., *Explain Dynamic Programming* or *Explain Deadlock*).\n"
        "- Ask **\"What should I revise today?\"** for spaced-repetition priorities.\n"
        "- Ask **\"Organize my timetable\"** for daily & weekly scheduling advice."
    )
    return {
        "reply": reply,
        "suggestions": [
            "Explain my weakest topic",
            "What should I revise today?",
            "Personalized study tips",
        ],
    }
