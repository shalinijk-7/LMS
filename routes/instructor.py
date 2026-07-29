from flask import Blueprint, render_template
from flask_login import login_required, current_user
from utils.decorators import instructor_required
from models import db, Course

instructor_bp = Blueprint('instructor', __name__, url_prefix='/instructor')

@instructor_bp.route('/dashboard')
@login_required
@instructor_required
def dashboard():
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    total_students = sum(len(course.enrollments) for course in courses)
    total_revenue = sum(course.price * len(course.enrollments) for course in courses if course.price)
    
    return render_template('dashboard/instructor_dashboard.html', 
                           courses=courses, 
                           total_students=total_students, 
                           total_revenue=total_revenue)

@instructor_bp.route('/students')
@login_required
@instructor_required
def students():
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    # Sort courses so that courses with enrollments appear first
    courses.sort(key=lambda c: len(c.enrollments), reverse=True)
    course_ids = [c.id for c in courses]
    
    from models import Enrollment, User
    # Get all enrollments for the instructor's courses
    enrollments = Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).order_by(Enrollment.enrolled_at.desc()).all()
    
    return render_template('dashboard/instructor_students.html', enrollments=enrollments, courses=courses)

@instructor_bp.route('/sessions', methods=['GET', 'POST'])
@login_required
@instructor_required
def sessions():
    from models import LiveSession
    from flask import request, flash, redirect, url_for
    from datetime import datetime
    
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        course_id = request.form.get('course_id')
        meeting_link = request.form.get('meeting_link')
        scheduled_date_str = request.form.get('scheduled_date')
        
        try:
            scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%dT%H:%M')
            new_session = LiveSession(
                title=title,
                course_id=course_id,
                instructor_id=current_user.id,
                meeting_link=meeting_link,
                scheduled_date=scheduled_date
            )
            db.session.add(new_session)
            db.session.commit()
            flash('Live session scheduled successfully!', 'success')
            return redirect(url_for('instructor.sessions'))
        except ValueError:
            flash('Invalid date format.', 'error')
            
    live_sessions = LiveSession.query.filter_by(instructor_id=current_user.id).order_by(LiveSession.scheduled_date.asc()).all()
    
    return render_template('dashboard/instructor_sessions.html', courses=courses, live_sessions=live_sessions)
