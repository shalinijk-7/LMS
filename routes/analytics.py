from flask import Blueprint, render_template
from flask_login import login_required, current_user

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

from models import db, User, Course, Enrollment, Progress, Role

@analytics_bp.route('/')
@login_required
def index():
    # Only admins or instructors should access this in a real system, but we'll allow based on current setup
    
    # 1. Total User Growth (simplified to just total counts for now)
    student_role = Role.query.filter_by(name='student').first()
    instructor_role = Role.query.filter_by(name='instructor').first()
    
    total_students = User.query.filter_by(role_id=student_role.id).count() if student_role else 0
    total_instructors = User.query.filter_by(role_id=instructor_role.id).count() if instructor_role else 0
    
    # 2. Course Metrics
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    total_completions = Progress.query.filter_by(completed=True).count()
    
    # 3. Financial Metrics (Revenue = price * enrollments)
    courses = Course.query.all()
    total_revenue = sum((course.price or 0.0) * len(course.enrollments) for course in courses)
    
    # Passing data to render chart
    # (We can pass simple JSON dumps for chart.js)
    chart_data = {
        'roles': ['Students', 'Instructors'],
        'role_counts': [total_students, total_instructors],
        'metrics': ['Courses', 'Enrollments', 'Completions'],
        'metric_counts': [total_courses, total_enrollments, total_completions]
    }
    
    return render_template('analytics/dashboard.html', 
                           total_students=total_students,
                           total_instructors=total_instructors,
                           total_courses=total_courses,
                           total_enrollments=total_enrollments,
                           total_completions=total_completions,
                           total_revenue=total_revenue,
                           chart_data=chart_data)
