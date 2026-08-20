# Tracks and manages student learning progress.
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import db, StudentProgress, CourseCompletion, Lesson, Course, Enrollment, Quiz, Result
from datetime import datetime

progress_bp = Blueprint('progress', __name__, url_prefix='/progress')

def check_course_completion(student_id, course_id):
    """Checks if a student has met all conditions to complete a course."""
    course = Course.query.get(course_id)
    if not course:
        return False
        
    # Check if CourseCompletion already exists
    existing_completion = CourseCompletion.query.filter_by(student_id=student_id, course_id=course_id).first()
    if existing_completion:
        return True
        
    # 1. All lessons completed
    total_lessons = Lesson.query.filter_by(course_id=course_id).count()
    completed_lessons = StudentProgress.query.filter_by(
        student_id=student_id, 
        course_id=course_id, 
        status='Completed'
    ).count()
    
    if total_lessons > 0 and completed_lessons < total_lessons:
        return False
        
    # 2. All quizzes passed (simplification: they just need to have taken the quizzes, or score > 50%)
    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    for quiz in quizzes:
        result = Result.query.filter_by(student_id=student_id, quiz_id=quiz.id).order_by(Result.score.desc()).first()
        if not result or (result.score / result.total) < 0.5: # 50% passing grade assumption
            return False
            
    # 3. Assignments submitted
    from models import Assignment, Submission
    assignments = Assignment.query.filter_by(course_id=course_id).all()
    for assignment in assignments:
        submission = Submission.query.filter_by(student_id=student_id, assignment_id=assignment.id).first()
        if not submission:
            return False

    # 4. Minimum attendance > 75%
    from models import Attendance
    total_classes = Attendance.query.filter_by(course_id=course_id).count()
    if total_classes > 0:
        attended = Attendance.query.filter(
            Attendance.course_id == course_id,
            Attendance.student_id == student_id,
            Attendance.status.in_(['Present', 'Late'])
        ).count()
        if (attended / total_classes) < 0.75:
            return False
            
    # If all passed, generate completion
    completion = CourseCompletion(
        student_id=student_id,
        course_id=course_id,
        completion_date=datetime.utcnow(),
        certificate_status='Issued',
        completion_percentage=100
    )
    db.session.add(completion)
    db.session.commit()
    
    # Notify student
    from services.notification_service import send_notification
    send_notification(
        user_id=student_id,
        title="Course Completed!",
        message=f"Congratulations! You have successfully completed {course.title}.",
        notification_type='success',
        icon='bi-trophy-fill',
        action_url=f'/course/{course.id}'
    )
    
    return True

@progress_bp.route('/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
@student_required
def mark_lesson_complete(lesson_id):
    """
    Handles the mark lesson complete functionality.
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    course_id = lesson.course_id
    
    # Find or create progress record
    progress = StudentProgress.query.filter_by(
        student_id=current_user.id,
        course_id=course_id,
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = StudentProgress(
            student_id=current_user.id,
            course_id=course_id,
            lesson_id=lesson_id,
            status='Completed',
            progress_percentage=100,
            last_accessed=datetime.utcnow()
        )
        db.session.add(progress)
    else:
        progress.status = 'Completed'
        progress.progress_percentage = 100
        progress.last_accessed = datetime.utcnow()
        
    db.session.commit()
    
    # Update overall enrollment progress_percent for compatibility if needed
    total_lessons = Lesson.query.filter_by(course_id=course_id).count()
    completed_lessons = StudentProgress.query.filter_by(
        student_id=current_user.id, 
        course_id=course_id, 
        status='Completed'
    ).count()
    
    overall_percentage = int((completed_lessons / total_lessons) * 100) if total_lessons > 0 else 100
    
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        enrollment.progress_percent = overall_percentage
        db.session.commit()
        
    # Check for course completion
    is_completed = check_course_completion(current_user.id, course_id)
    
    return jsonify({
        'success': True,
        'overall_percentage': overall_percentage,
        'course_completed': is_completed
    })

@progress_bp.route('/lesson/<int:lesson_id>/update_time', methods=['POST'])
@login_required
@student_required
def update_learning_time(lesson_id):
    """
    Handles the update learning time functionality.
    """
    data = request.get_json()
    time_spent = data.get('time_spent', 0) # in seconds
    
    lesson = Lesson.query.get_or_404(lesson_id)
    
    progress = StudentProgress.query.filter_by(
        student_id=current_user.id,
        course_id=lesson.course_id,
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = StudentProgress(
            student_id=current_user.id,
            course_id=lesson.course_id,
            lesson_id=lesson_id,
            status='In Progress',
            learning_time=time_spent,
            last_accessed=datetime.utcnow()
        )
        db.session.add(progress)
    else:
        if progress.status == 'Not Started':
            progress.status = 'In Progress'
        progress.learning_time += time_spent
        progress.last_accessed = datetime.utcnow()
        
    db.session.commit()
    return jsonify({'success': True})
