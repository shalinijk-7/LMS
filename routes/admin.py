# Handles all administrator-related operations and management features.
from flask import Blueprint, render_template
from flask_login import login_required
from utils.decorators import admin_required
from models import db, User, Course

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    users_count = User.query.count()
    courses_count = Course.query.count()
    
    from models import Role, CourseCompletion, Enrollment
    instructor_role = Role.query.filter_by(name='instructor').first()
    student_role = Role.query.filter_by(name='student').first()
    
    instructors = User.query.filter_by(role_id=instructor_role.id).all() if instructor_role else []
    students = User.query.filter_by(role_id=student_role.id).all() if student_role else []
    
    total_completions = CourseCompletion.query.count()
    total_enrollments = Enrollment.query.count()
    avg_completion_rate = int((total_completions / total_enrollments) * 100) if total_enrollments > 0 else 0
    
    return render_template('dashboard/admin_dashboard.html', 
                           users_count=users_count, 
                           courses_count=courses_count,
                           instructors=instructors,
                           students=students,
                           total_completions=total_completions,
                           avg_completion_rate=avg_completion_rate)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('dashboard/admin_users.html', users=users)

@admin_bp.route('/courses')
@login_required
@admin_required
def courses():
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('dashboard/admin_courses.html', courses=courses)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    from models import Enrollment, CourseCompletion, StudentProgress, Role, Certificate, Submission, Result
    from sqlalchemy import func
    from datetime import datetime, timedelta
    total_users = User.query.count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    total_completions = CourseCompletion.query.count()
    total_certificates = Certificate.query.count()
    student_role = Role.query.filter_by(name='student').first()
    instructor_role = Role.query.filter_by(name='instructor').first()
    total_students = User.query.filter_by(role_id=student_role.id).count() if student_role else 0
    total_instructors = User.query.filter_by(role_id=instructor_role.id).count() if instructor_role else 0
    active_learners = StudentProgress.query.filter(
        StudentProgress.progress_percentage > 0,
        StudentProgress.progress_percentage < 100
    ).group_by(StudentProgress.student_id).count()
    courses = Course.query.all()
    total_revenue = sum((course.price or 0) * len(course.enrollments) for course in courses)
    completion_rate = round((total_completions / total_enrollments) * 100, 1) if total_enrollments > 0 else 0
    # Top 5 courses
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
    # Recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    # Enrollment trend (7 days)
    today = datetime.utcnow().date()
    trend_labels = []
    trend_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Enrollment.query.filter(func.date(Enrollment.enrolled_at) == day).count()
        trend_labels.append(day.strftime('%a'))
        trend_data.append(count)
    chart_data = {
        'trend_labels': trend_labels,
        'trend_data': trend_data,
        'role_labels': ['Students', 'Instructors'],
        'role_data': [total_students, total_instructors],
        'top_labels': [c[0][:18] for c in top_courses],
        'top_data': [c[1] for c in top_courses],
    }
    return render_template(
        'dashboard/admin_reports.html',
        total_users=total_users,
        total_courses=total_courses,
        total_enrollments=total_enrollments,
        total_completions=total_completions,
        total_certificates=total_certificates,
        total_students=total_students,
        total_instructors=total_instructors,
        active_learners=active_learners,
        total_revenue=total_revenue,
        completion_rate=completion_rate,
        top_courses=top_courses,
        recent_users=recent_users,
        chart_data=chart_data
    )