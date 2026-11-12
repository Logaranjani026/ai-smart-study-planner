from flask import Blueprint, render_template, redirect, url_for
from utils.auth_helpers import get_current_student, login_required_page

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def landing():
    student = get_current_student()
    return render_template("landing.html", current_student=student)


@pages_bp.route("/login")
def login_page():
    if get_current_student():
        return redirect(url_for("pages.dashboard"))
    return render_template("auth.html", mode="login")


@pages_bp.route("/register")
def register_page():
    if get_current_student():
        return redirect(url_for("pages.dashboard"))
    return render_template("auth.html", mode="register")


@pages_bp.route("/forgot-password")
def forgot_password_page():
    if get_current_student():
        return redirect(url_for("pages.dashboard"))
    return render_template("auth.html", mode="forgot")


@pages_bp.route("/dashboard")
@login_required_page
def dashboard(student):
    return render_template("dashboard.html", current_student=student)


@pages_bp.route("/subjects")
@login_required_page
def subjects_page(student):
    return render_template("subjects.html", current_student=student)


@pages_bp.route("/planner")
@login_required_page
def planner_page(student):
    return render_template("planner.html", current_student=student)


@pages_bp.route("/weak-topics")
@login_required_page
def weak_topics_page(student):
    return render_template("weak_topics.html", current_student=student)


@pages_bp.route("/assistant")
@login_required_page
def assistant_page(student):
    return render_template("assistant.html", current_student=student)


@pages_bp.route("/progress")
@login_required_page
def progress_page(student):
    return render_template("progress.html", current_student=student)


@pages_bp.route("/reminders")
@login_required_page
def reminders_page(student):
    return render_template("reminders.html", current_student=student)

