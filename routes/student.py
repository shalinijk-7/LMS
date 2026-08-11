# Handles student-specific features and learning dashboard.
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import db, Enrollment, Result, Submission
from datetime import datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    from models import CourseCompletion, StudentProgress, Attendance, Assignment

    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()

    dashboard_data = []
    total_learning_time = 0
    completed_courses_count = 0
    in_progress_count = 0
    overall_attendance_pct = 100
    total_attended = 0
    total_classes = 0

    for enrollment in enrollments:
        course_id = enrollment.course_id

        completion = CourseCompletion.query.filter_by(
            student_id=current_user.id, course_id=course_id
        ).first()
        is_completed = completion is not None
        if is_completed:
            completed_courses_count += 1
        else:
            in_progress_count += 1

        progress_records = StudentProgress.query.filter_by(
            student_id=current_user.id, course_id=course_id
        ).all()
        course_time = sum([p.learning_time for p in progress_records if p.learning_time])
        total_learning_time += course_time

        last_accessed = None
        if progress_records:
            last_accessed = max(
                [p.last_accessed for p in progress_records if p.last_accessed] or [None]
            )

        course_classes = Attendance.query.filter_by(course_id=course_id).count()
        course_attended = Attendance.query.filter(
            Attendance.course_id == course_id,
            Attendance.student_id == current_user.id,
            Attendance.status.in_(['Present', 'Late'])
        ).count()

        total_classes += course_classes
        total_attended += course_attended

        upcoming_assignments = Assignment.query.filter(
            Assignment.course_id == course_id,
            Assignment.deadline > datetime.utcnow()
        ).all()

        dashboard_data.append({
            'course': enrollment.course,
            'progress_percent': enrollment.progress_percent,
            'is_completed': is_completed,
            'learning_time_mins': course_time // 60,
            'last_accessed': last_accessed,
            'upcoming_assignments': upcoming_assignments,
            'attendance_pct': int((course_attended / course_classes) * 100) if course_classes > 0 else 100
        })

    if total_classes > 0:
        overall_attendance_pct = int((total_attended / total_classes) * 100)

    return render_template(
        'dashboard/student_dashboard.html',
        enrollments=enrollments,
        dashboard_data=dashboard_data,
        total_learning_time_hrs=total_learning_time // 3600,
        completed_courses_count=completed_courses_count,
        in_progress_count=in_progress_count,
        overall_attendance_pct=overall_attendance_pct
    )


@student_bp.route('/sessions')
@login_required
@student_required
def sessions():
    from models import LiveSession

    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    course_ids = [e.course_id for e in enrollments]

    live_sessions = LiveSession.query.filter(
        LiveSession.course_id.in_(course_ids),
        LiveSession.scheduled_date >= datetime.utcnow()
    ).order_by(LiveSession.scheduled_date.asc()).all()

    return render_template(
        'dashboard/student_sessions.html',
        live_sessions=live_sessions
    )


@student_bp.route('/analytics')
@login_required
@student_required
def analytics():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    quiz_results = Result.query.filter_by(
        student_id=current_user.id
    ).order_by(Result.submitted_at.desc()).all()
    submissions = Submission.query.filter_by(
        student_id=current_user.id
    ).order_by(Submission.submitted_at.desc()).all()

    return render_template(
        'dashboard/student_analytics.html',
        enrollments=enrollments,
        quiz_results=quiz_results,
        submissions=submissions
    )


@student_bp.route('/attendance')
@login_required
@student_required
def attendance():
    from models import Attendance

    course_id = request.args.get('course_id', type=int)

    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_course_ids = [e.course_id for e in enrollments]

    query = Attendance.query.filter_by(student_id=current_user.id)
    if course_id and course_id in enrolled_course_ids:
        query = query.filter_by(course_id=course_id)

    records = query.order_by(Attendance.attendance_date.desc()).all()

    total_classes = len(records)
    attended = sum(1 for r in records if r.status in ['Present', 'Late'])
    attendance_pct = int((attended / total_classes) * 100) if total_classes > 0 else 100

    return render_template(
        'dashboard/student_attendance.html',
        records=records,
        enrollments=enrollments,
        selected_course_id=course_id,
        total_classes=total_classes,
        attended=attended,
        attendance_pct=attendance_pct
    )


@student_bp.route('/payment-history')
@login_required
@student_required
def payment_history():
    # Payment model may not exist in all versions — handle safely
    try:
        from models.all_models import Payment
        payments = Payment.query.filter_by(
            student_id=current_user.id
        ).order_by(Payment.payment_date.desc()).all()
    except Exception:
        payments = []

    return render_template(
        'dashboard/student_payment_history.html',
        payments=payments
    )