"""
Admin Blueprint
Handles routing and views for administrative tasks, such as managing users, 
courses, and viewing platform reports.
"""
# Import core Flask components and decorator requirements
from flask import Blueprint, render_template
from flask_login import login_required

# Import admin authorization checker
from utils.decorators import admin_required

# Import core models for platform entities
from models import db, User, Course

# Define the admin blueprint with its base URL prefix
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
    # Fetch top-level metric counts for quick analysis
    users_count = User.query.count()
    courses_count = Course.query.count()
    
    # Import relational models locally to prevent potential circular dependency issues
    from models import Role, CourseCompletion, Enrollment
    
    # Locate specific database roles to filter different user segments
    instructor_role = Role.query.filter_by(name='instructor').first()
    student_role = Role.query.filter_by(name='student').first()
    
    # Retrieve user accounts mapped to instructor and student roles
    instructors = User.query.filter_by(role_id=instructor_role.id).all() if instructor_role else []
    students = User.query.filter_by(role_id=student_role.id).all() if student_role else []
    
    # Calculate totals for tracking user educational progress
    total_completions = CourseCompletion.query.count()
    total_enrollments = Enrollment.query.count()
    
    # Safely compute percentage to protect against division by zero errors
    avg_completion_rate = int((total_completions / total_enrollments) * 100) if total_enrollments > 0 else 0
    
    # Render the consolidated dashboard panel template passing statistics
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
    # Query all platform users ordered by registration date (newest first)
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
    # Query all created courses sorted chronologically
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
    # Local imports to fetch transactional tables and relationship data
    from models import Enrollment, Payment
    
    # Fetch enrollment history details
    enrollments = Enrollment.query.order_by(Enrollment.enrolled_at.desc()).all()
    
    report_data = []
    # Build complete reports payloads mapping enrollments to transaction payments
    for enr in enrollments:
        # Resolve payment associated with the active student and specific course
        payment = Payment.query.filter_by(student_id=enr.user_id, course_id=enr.course_id).first()
        
        # Evaluate status depending on existing invoice or fallback value for free resources
        payment_status = payment.status if payment else ('Free' if enr.course.course_type == 'Free' else 'Pending')
        
        # Populate formatted dataset dictionary
        report_data.append({
            'student_name': enr.student.name if enr.student else 'Unknown',
            'course_title': enr.course.title if enr.course else 'Unknown',
            'instructor_name': enr.course.instructor.name if enr.course and enr.course.instructor else 'Unknown',
            'course_type': enr.course.course_type if enr.course else 'Free',
            # Format date for cleaner layout display and keep ISO raw representation for data filtering
            'enrolled_at': enr.enrolled_at.strftime('%b %d, %Y<br>%I:%M %p') if enr.enrolled_at else 'Unknown',
            'raw_date': enr.enrolled_at.isoformat() if enr.enrolled_at else '1970-01-01',
            'payment_status': payment_status,
            'progress': enr.progress_percent,
            'amount': payment.amount if payment else 0.0,
            'completion_status': 'Completed' if enr.progress_percent == 100 else 'In Progress'
        })
        
    # Render final compiled analytical records
    return render_template('dashboard/admin_reports.html', report_data=report_data)