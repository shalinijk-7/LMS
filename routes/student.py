from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import db, Enrollment

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
def dashboard():
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard/student_dashboard.html', enrollments=enrollments)

@student_bp.route('/sessions')
@login_required
def sessions():
    if current_user.role.name != 'student':
        from flask import flash, redirect, url_for
        flash('Only students can view this page.', 'error')
        return redirect(url_for('dashboard.index'))
        
    from models import LiveSession, Enrollment
    # Get course IDs the student is enrolled in
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    course_ids = [e.course_id for e in enrollments]
    
    # Get upcoming live sessions for those courses
    from datetime import datetime
    live_sessions = LiveSession.query.filter(LiveSession.course_id.in_(course_ids), LiveSession.scheduled_date >= datetime.utcnow()).order_by(LiveSession.scheduled_date.asc()).all()
    
    return render_template('dashboard/student_sessions.html', live_sessions=live_sessions)
