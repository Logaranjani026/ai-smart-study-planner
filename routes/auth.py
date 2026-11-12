import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, session, redirect, url_for
from models import db, Student
from utils.auth_helpers import validate_email, get_current_student

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    department = (data.get("department") or "").strip()
    year_of_study = (data.get("year_of_study") or "").strip()

    if len(full_name) < 2:
        return jsonify({"error": "Please enter your full name (at least 2 characters)."}), 400
    if not validate_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if not department:
        return jsonify({"error": "Please select your department."}), 400
    if not year_of_study:
        return jsonify({"error": "Please select your year of study."}), 400

    if Student.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    student = Student(
        full_name=full_name,
        email=email,
        department=department,
        year_of_study=year_of_study,
    )
    student.set_password(password)
    db.session.add(student)
    db.session.commit()

    session["student_id"] = student.student_id
    return jsonify({"message": "Registration successful", "student": student.to_dict()}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not validate_email(email) or not password:
        return jsonify({"error": "Email and password are required."}), 400

    student = Student.query.filter_by(email=email).first()
    if not student or not student.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    session["student_id"] = student.student_id
    return jsonify({"message": "Login successful", "student": student.to_dict()}), 200


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    if not validate_email(email):
        return jsonify({"error": "Please enter a valid email address."}), 400

    student = Student.query.filter_by(email=email).first()
    if not student:
        return jsonify({"error": "No student account found with that email address."}), 404

    token = secrets.token_urlsafe(16)
    student.reset_token = token
    student.reset_token_expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    db.session.commit()

    return jsonify(
        {
            "message": "Reset token generated (valid for 30 minutes).",
            "reset_token": token,
        }
    ), 200


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True) or {}
    token = (data.get("token") or "").strip()
    new_password = data.get("new_password") or ""

    if not token or len(new_password) < 6:
        return jsonify({"error": "Valid reset token and new password (min 6 chars) are required."}), 400

    student = Student.query.filter_by(reset_token=token).first()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    if not student or not student.reset_token_expiry or student.reset_token_expiry < now_utc:
        return jsonify({"error": "Invalid or expired reset token."}), 400

    student.set_password(new_password)
    student.reset_token = None
    student.reset_token_expiry = None
    db.session.commit()

    return jsonify({"message": "Password reset successfully."}), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
def current_user():
    student = get_current_student()
    if not student:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "student": student.to_dict()}), 200


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("student_id", None)
    return redirect(url_for("pages.landing"))
