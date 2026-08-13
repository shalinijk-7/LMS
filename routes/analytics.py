from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from utils.decorators import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func, cast, Date, desc

from models import (
    db, User, Role, Course, Enrollment, Progress, Payment, 
    CourseCompletion, StudentProgress, Attendance, Quiz, Assignment, 
    Submission, Result, ActivityLog
)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/analytics')

@analytics_bp.route('/')
@login_required
@admin_required
def index():
    """
    Renders the main analytics dashboard template. Data is fetched via AJAX.
    """
    return render_template('analytics/dashboard.html')

@analytics_bp.route('/api/data')
@login_required
@admin_required
def get_analytics_data():
    """
    Returns JSON data for the analytics dashboard charts and KPIs, filtered by date.
    """
    period = request.args.get('period', '30d')
    today = datetime.utcnow().date()
    
    if period == '7d':
        start_date = today - timedelta(days=7)
    elif period == '30d':
        start_date = today - timedelta(days=30)
    elif period == '6m':
        start_date = today - timedelta(days=180)
    elif period == '1y':
        start_date = today - timedelta(days=365)
    else:
        # Default fallback or Custom
        start_date = datetime(2000, 1, 1).date()

    start_datetime = datetime.combine(start_date, datetime.min.time())
    
    def df(query, col):
        return query.filter(col >= start_datetime)

    roles = {r.name: r.id for r in Role.query.all()}
    
    # 1. KPIs
    total_students = df(User.query, User.created_at).filter_by(role_id=roles.get('student')).count()
    total_instructors = df(User.query, User.created_at).filter_by(role_id=roles.get('instructor')).count()
    total_admins = df(User.query, User.created_at).filter_by(role_id=roles.get('admin')).count()
    
    total_courses = df(Course.query, Course.created_at).count()
    total_enrollments = df(Enrollment.query, Enrollment.enrolled_at).count()
    completed_courses = df(CourseCompletion.query, CourseCompletion.completion_date).count()
    
    active_learners = df(StudentProgress.query, StudentProgress.last_accessed).filter(StudentProgress.status == 'In Progress').count()
    
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(Payment.status == 'Success').filter(Payment.payment_date >= start_datetime).scalar() or 0
    
    avg_completion_rate = int((completed_courses / total_enrollments) * 100) if total_enrollments > 0 else 0
    
    # Attendance Rate
    attendance_stats = db.session.query(Attendance.status, func.count(Attendance.id)).filter(Attendance.attendance_date >= start_date).group_by(Attendance.status).all()
    att_dict = {status: count for status, count in attendance_stats}
    total_attendance_records = sum(att_dict.values())
    present_count = att_dict.get('Present', 0)
    avg_attendance_rate = int((present_count / total_attendance_records) * 100) if total_attendance_records > 0 else 0

    # 2. User Growth Line Chart (simplified to day grouping for now)
    user_growth_query = db.session.query(
        func.date(User.created_at).label('date'),
        Role.name,
        func.count(User.id)
    ).join(Role).filter(User.created_at >= start_datetime).group_by(func.date(User.created_at), Role.name).all()
    
    # 3. Enrollment Trends
    enrollment_trends = db.session.query(
        func.date(Enrollment.enrolled_at),
        func.count(Enrollment.id)
    ).filter(Enrollment.enrolled_at >= start_datetime).group_by(func.date(Enrollment.enrolled_at)).all()

    # 4. Course Performance (Top 5 by Enrollments)
    top_courses = db.session.query(
        Course.title,
        func.count(Enrollment.id).label('enrollment_count')
    ).outerjoin(Enrollment).group_by(Course.id).order_by(desc('enrollment_count')).limit(5).all()

    # 5. Revenue Analytics
    revenue_trends = db.session.query(
        func.date(Payment.payment_date),
        func.sum(Payment.amount)
    ).filter(Payment.status == 'Success', Payment.payment_date >= start_datetime).group_by(func.date(Payment.payment_date)).all()
    
    # 6. Course Completion
    completion_stats = db.session.query(
        StudentProgress.status, func.count(StudentProgress.id)
    ).filter(StudentProgress.last_accessed >= start_datetime).group_by(StudentProgress.status).all()

    # 7. Quiz & Assignment Performance
    total_quizzes = Quiz.query.count()
    completed_quizzes = Result.query.filter(Result.submitted_at >= start_datetime).count()
    
    total_assignments = Assignment.query.count()
    submitted_assignments = Submission.query.filter(Submission.submitted_at >= start_datetime).count()

    # 10. Recent Activity
    recent_activity = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    recent_activities = [{
        'action': act.action,
        'user': act.user.name if act.user else 'System',
        'time': act.timestamp.strftime('%Y-%m-%d %H:%M')
    } for act in recent_activity]

    # 11. Top Instructors
    top_instructors = db.session.query(
        User.name,
        func.count(Course.id).label('courses_count')
    ).join(Course, Course.instructor_id == User.id).group_by(User.id).order_by(desc('courses_count')).limit(5).all()

    data = {
        'kpis': {
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_admins': total_admins,
            'total_courses': total_courses,
            'total_enrollments': total_enrollments,
            'completed_courses': completed_courses,
            'active_learners': active_learners,
            'total_revenue': float(total_revenue),
            'avg_completion_rate': avg_completion_rate,
            'avg_attendance_rate': avg_attendance_rate
        },
        'charts': {
            'user_growth': [{'date': str(row[0]), 'role': row[1], 'count': row[2]} for row in user_growth_query],
            'enrollment_trends': [{'date': str(row[0]), 'count': row[1]} for row in enrollment_trends],
            'course_performance': [{'title': row[0], 'enrollments': row[1]} for row in top_courses],
            'revenue_trends': [{'date': str(row[0]), 'revenue': float(row[1])} for row in revenue_trends],
            'course_completion': {row[0]: row[1] for row in completion_stats},
            'attendance': att_dict,
            'academic': {
                'quizzes': {'total': total_quizzes, 'completed': completed_quizzes},
                'assignments': {'total': total_assignments, 'submitted': submitted_assignments}
            }
        },
        'tables': {
            'recent_activity': recent_activities,
            'top_instructors': [{'name': row[0], 'courses': row[1]} for row in top_instructors]
        }
    }
    
    return jsonify(data)
