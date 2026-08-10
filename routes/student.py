# Handles student-specific features and learning activities.
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from models import db, Enrollment, Result, Submission

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
def dashboard():
    from models import CourseCompletion, StudentProgress, Attendance, Assignment, Quiz
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    
    # Pre-calculate data for the template
    dashboard_data = []
    total_learning_time = 0
    completed_courses_count = 0
    in_progress_count = 0
    
    overall_attendance_pct = 100
    total_attended = 0
    total_classes = 0
    
    for enrollment in enrollments:
        course_id = enrollment.course_id
        
        # Completion status
        completion = CourseCompletion.query.filter_by(student_id=current_user.id, course_id=course_id).first()
        is_completed = completion is not None
        if is_completed:
            completed_courses_count += 1
        else:
            in_progress_count += 1
            
        # Progress and learning time
        progress_records = StudentProgress.query.filter_by(student_id=current_user.id, course_id=course_id).all()
        course_time = sum([p.learning_time for p in progress_records if p.learning_time])
        total_learning_time += course_time
        
        last_accessed = None
        if progress_records:
            last_accessed = max([p.last_accessed for p in progress_records if p.last_accessed] or [None])
            
        # Attendance for this course
        course_classes = Attendance.query.filter_by(course_id=course_id).count()
        course_attended = Attendance.query.filter(
            Attendance.course_id == course_id,
            Attendance.student_id == current_user.id,
            Attendance.status.in_(['Present', 'Late'])
        ).count()
        
        total_classes += course_classes
        total_attended += course_attended
        
        # Upcoming assignments (just an example, fetching deadlines in future)
        from datetime import datetime
        upcoming_assignments = Assignment.query.filter(Assignment.course_id == course_id, Assignment.deadline > datetime.utcnow()).all()
        
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
        
    return render_template('dashboard/student_dashboard.html', 
                           enrollments=enrollments,
                           dashboard_data=dashboard_data,
                           total_learning_time_hrs=total_learning_time // 3600,
                           completed_courses_count=completed_courses_count,
                           in_progress_count=in_progress_count,
                           overall_attendance_pct=overall_attendance_pct)

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

@student_bp.route('/analytics')
@login_required
def analytics():
    if current_user.role.name != 'student':
        from flask import flash, redirect, url_for
        flash('Only students can view this page.', 'error')
        return redirect(url_for('dashboard.index'))
        
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    quiz_results = Result.query.filter_by(student_id=current_user.id).order_by(Result.submitted_at.desc()).all()
    submissions = Submission.query.filter_by(student_id=current_user.id).order_by(Submission.submitted_at.desc()).all()
    
    return render_template('dashboard/student_analytics.html', 
                           enrollments=enrollments,
                           quiz_results=quiz_results,
                           submissions=submissions)

@student_bp.route('/attendance')
@login_required
def attendance():
    if current_user.role.name != 'student':
        from flask import flash, redirect, url_for
        flash('Only students can view this page.', 'error')
        return redirect(url_for('dashboard.index'))
        
    from models import Attendance, Enrollment, Course
    from flask import request
    
    # Optional course filter
    course_id = request.args.get('course_id', type=int)
    
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_course_ids = [e.course_id for e in enrollments]
    
    query = Attendance.query.filter_by(student_id=current_user.id)
    if course_id and course_id in enrolled_course_ids:
        query = query.filter_by(course_id=course_id)
        
    records = query.order_by(Attendance.attendance_date.desc()).all()
    
    # Calculate summary
    total_classes = len(records)
    attended = sum(1 for r in records if r.status in ['Present', 'Late'])
    attendance_pct = int((attended / total_classes) * 100) if total_classes > 0 else 100
    
    return render_template('dashboard/student_attendance.html', 
                           records=records,
                           enrollments=enrollments,
                           selected_course_id=course_id,
                           total_classes=total_classes,
                           attended=attended,
                           attendance_pct=attendance_pct)
