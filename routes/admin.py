"""
Admin Blueprint
Handles routing and views for administrative tasks, such as managing users, 
courses, and viewing platform reports.
"""
from flask import Blueprint, render_template
from flask_login import login_required
from utils.decorators import admin_required
from models import db, User, Course

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """
    Renders the admin dashboard with high-level platform statistics.
    
    Retrieves counts for users, courses, enrollments, and completions to
    display key metrics and calculate the average completion rate.
    
    Returns:
        Rendered HTML template for the admin dashboard.
    """
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
    """
    Displays a list of all registered users on the platform.
    
    Returns:
        Rendered HTML template for the admin user management page.
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('dashboard/admin_users.html', users=users)

@admin_bp.route('/courses')
@login_required
@admin_required
def courses():
    """
    Displays a list of all courses available on the platform.
    
    Returns:
        Rendered HTML template for the admin course management page.
    """
    courses = Course.query.order_by(Course.created_at.desc()).all()
    return render_template('dashboard/admin_courses.html', courses=courses)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """
    Generates and displays comprehensive reports in a datatable view.
    
    Returns:
        Rendered HTML template for the admin reports page.
    """
    from models import Enrollment, Payment
    
    enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).all()
    
    report_data = []
    for enr in enrollments:
        payment = Payment.query.filter_by(student_id=enr.user_id, course_id=enr.course_id).first()
        payment_status = payment.status if payment else ('Free' if enr.course.course_type == 'Free' else 'Pending')
        
        report_data.append({
            'student_name': enr.student.name if enr.student else 'Unknown',
            'course_title': enr.course.title if enr.course else 'Unknown',
            'instructor_name': enr.course.instructor.name if enr.course and enr.course.instructor else 'Unknown',
            'course_type': enr.course.course_type if enr.course else 'Free',
            'enrolled_at': enr.enrolled_at.strftime('%b %d, %Y<br>%I:%M %p') if enr.enrolled_at else 'Unknown',
            'raw_date': enr.enrolled_at.isoformat() if enr.enrolled_at else '1970-01-01',
            'payment_status': payment_status,
            'progress': enr.progress_percent,
            'amount': payment.amount if payment else 0.0,
            'completion_status': 'Completed' if enr.progress_percent == 100 else 'In Progress'
        })
        
    return render_template('dashboard/admin_reports.html', report_data=report_data)
