from ai_engine.weak_topic_detector import (
    compute_topic_weakness,
    analyze_student_topics,
    refresh_topic_weakness,
)
from ai_engine.revision_predictor import (
    predict_topic_next_revision,
    get_revision_recommendations,
)
from ai_engine.timetable_generator import (
    generate_smart_timetable,
    adapt_student_timetable,
    compute_topic_priority_rationale,
)
from ai_engine.study_assistant import generate_assistant_reply

__all__ = [
    "compute_topic_weakness",
    "analyze_student_topics",
    "refresh_topic_weakness",
    "predict_topic_next_revision",
    "get_revision_recommendations",
    "generate_smart_timetable",
    "adapt_student_timetable",
    "compute_topic_priority_rationale",
    "generate_assistant_reply",
]

