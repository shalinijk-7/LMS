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
    total_users = User.query.count()
    total_courses = Course.query.count()
    from models import Enrollment, CourseCompletion, StudentProgress, Attendance
    total_enrollments = Enrollment.query.count()
    total_completions = CourseCompletion.query.count()
    
    # Calculate active learners (those with progress > 0 but not 100)
    active_learners = StudentProgress.query.filter(StudentProgress.progress_percentage > 0, StudentProgress.progress_percentage < 100).group_by(StudentProgress.student_id).count()
    
    # Calculate revenue (assuming price * enrollments)
    courses = Course.query.all()
    total_revenue = sum(course.price * len(course.enrollments) for course in courses if course.price)
    
    return render_template('dashboard/admin_reports.html', 
                           total_users=total_users,
                           total_courses=total_courses,
                           total_enrollments=total_enrollments,
                           total_completions=total_completions,
                           active_learners=active_learners,
                           total_revenue=total_revenue)
