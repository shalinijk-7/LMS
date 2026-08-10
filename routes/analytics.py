from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import db, User, Course, Enrollment, Progress, Role, CourseCompletion, Submission, Result, Certificate
from sqlalchemy import func
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
@login_required
def index():
    student_role = Role.query.filter_by(name='student').first()
    instructor_role = Role.query.filter_by(name='instructor').first()

    total_students = User.query.filter_by(role_id=student_role.id).count() if student_role else 0
    total_instructors = User.query.filter_by(role_id=instructor_role.id).count() if instructor_role else 0
    total_users = total_students + total_instructors

    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    total_completions = CourseCompletion.query.count()
    total_certificates = Certificate.query.count()
    total_submissions = Submission.query.count()
    total_quiz_attempts = Result.query.count()

    # Revenue
    courses = Course.query.all()
    total_revenue = sum((course.price or 0.0) * len(course.enrollments) for course in courses)

    # Completion rate
    completion_rate = round((total_completions / total_enrollments) * 100, 1) if total_enrollments > 0 else 0

    # Top courses by enrollments
    top_courses = (
        db.session.query(
            Course.title,
            func.count(Enrollment.id).label('enroll_count'),
            Course.price
        )
        .outerjoin(Enrollment, Course.id == Enrollment.course_id)
        .group_by(Course.id)
        .order_by(func.count(Enrollment.id).desc())
        .limit(5)
        .all()
    )

    # Recent enrollments (last 7 days trend)
    today = datetime.utcnow().date()
    enrollment_trend_labels = []
    enrollment_trend_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Enrollment.query.filter(
            func.date(Enrollment.enrolled_at) == day
        ).count()
        enrollment_trend_labels.append(day.strftime('%b %d'))
        enrollment_trend_data.append(count)

    # User growth (last 6 months simplified)
    user_growth_labels = []
    user_growth_data = []
    for i in range(5, -1, -1):
        month_start = (datetime.utcnow().replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        if i == 0:
            month_end = datetime.utcnow()
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month.replace(day=1) - timedelta(days=1)
        count = User.query.filter(
            User.created_at >= month_start,
            User.created_at <= month_end
        ).count()
        user_growth_labels.append(month_start.strftime('%b %Y'))
        user_growth_data.append(count)

    chart_data = {
        'roles': ['Students', 'Instructors'],
        'role_counts': [total_students, total_instructors],
        'metrics': ['Courses', 'Enrollments', 'Completions', 'Certificates'],
        'metric_counts': [total_courses, total_enrollments, total_completions, total_certificates],
        'enrollment_trend_labels': enrollment_trend_labels,
        'enrollment_trend_data': enrollment_trend_data,
        'user_growth_labels': user_growth_labels,
        'user_growth_data': user_growth_data,
        'top_course_labels': [c[0][:20] for c in top_courses],
        'top_course_data': [c[1] for c in top_courses],
    }

    return render_template(
        'analytics/dashboard.html',
        total_users=total_users,
        total_students=total_students,
        total_instructors=total_instructors,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        total_completions=total_completions,
        total_certificates=total_certificates,
        total_submissions=total_submissions,
        total_quiz_attempts=total_quiz_attempts,
        total_revenue=total_revenue,
        completion_rate=completion_rate,
        top_courses=top_courses,
        chart_data=chart_data
    )