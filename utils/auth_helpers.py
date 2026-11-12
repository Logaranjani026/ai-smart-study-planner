import re
from datetime import date, datetime
from functools import wraps
from flask import session, redirect, url_for, jsonify
from models import db, Student


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> bool:
    return bool(email and EMAIL_REGEX.match(email.strip()))


def parse_date_str(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def get_current_student() -> Student | None:
    student_id = session.get("student_id")
    if not student_id:
        return None
    return db.session.get(Student, student_id)


def login_required_page(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        student = get_current_student()
        if not student:
            return redirect(url_for("pages.login_page"))
        return view_fn(student=student, *args, **kwargs)

    return wrapper


def login_required_api(view_fn):
    @wraps(view_fn)
    def wrapper(*args, **kwargs):
        student = get_current_student()
        if not student:
            return jsonify({"error": "Authentication required"}), 401
        return view_fn(student=student, *args, **kwargs)

    return wrapper
