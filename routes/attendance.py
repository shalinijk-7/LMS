from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from utils.decorators import instructor_required
from models import db, Course, Lesson, Attendance, Enrollment, User
from datetime import datetime

# Initialize the attendance blueprint with a URL prefix
attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/course/<int:course_id>/manage', methods=['GET', 'POST'])
@login_required
@instructor_required
def manage_attendance(course_id):
    """
    Handles the manage attendance functionality.
    Allows instructors to record or update student attendance for specific course dates and lessons.
    """
    # Ensure the course exists and belongs to the currently logged-in instructor
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    
    # Retrieve all enrolled students for this course
    students = [e.student for e in enrollments]
    
    # Get the selected date and optional lesson ID from query parameters (defaults to current date)
    selected_date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    selected_lesson_id = request.args.get('lesson_id', type=int)
    
    # Safely parse the selected date parameter
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.utcnow().date()
        
    # Build query to fetch existing attendance records for the selected date and optional lesson
    query = Attendance.query.filter_by(course_id=course.id, attendance_date=selected_date)
    if selected_lesson_id:
        query = query.filter_by(lesson_id=selected_lesson_id)
        
    existing_records = query.all()
    
    # Map student IDs to existing attendance records for easier template lookup
    attendance_dict = {record.student_id: record for record in existing_records}
    
    # Process form submissions when attendance status is submitted/updated
    if request.method == 'POST':
        date_str = request.form.get('attendance_date')
        lesson_id = request.form.get('lesson_id', type=int)
        
        # Safely parse submitted date, defaulting to today if invalid
        try:
            att_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            att_date = datetime.utcnow().date()
            
        # Iterate over all students to record or update their status and remarks
        for student in students:
            status = request.form.get(f'status_{student.id}')
            remarks = request.form.get(f'remarks_{student.id}')
            
            if status:
                # Query to verify if an attendance entry already exists for this student, course, date, and lesson
                record_query = Attendance.query.filter_by(
                    course_id=course.id,
                    student_id=student.id,
                    attendance_date=att_date
                )
                if lesson_id:
                    record_query = record_query.filter_by(lesson_id=lesson_id)
                    
                record = record_query.first()
                
                if record:
                    # Update details for already existing attendance record
                    record.status = status
                    record.remarks = remarks
                else:
                    # Instantiate and queue a new attendance record
                    record = Attendance(
                        student_id=student.id,
                        course_id=course.id,
                        lesson_id=lesson_id,
                        instructor_id=current_user.id,
                        attendance_date=att_date,
                        status=status,
                        remarks=remarks
                    )
                    db.session.add(record)
                    
        # Commit all new and modified records to the database
        db.session.commit()
        flash('Attendance saved successfully!', 'success')
        return redirect(url_for('attendance.manage_attendance', course_id=course.id, date=date_str, lesson_id=lesson_id))
        
    # Render view for current date and lesson filters
    return render_template('attendance/manage_attendance.html', 
                           course=course, 
                           lessons=lessons, 
                           students=students,
                           selected_date=selected_date,
                           selected_lesson_id=selected_lesson_id,
                           attendance_dict=attendance_dict)

@attendance_bp.route('/course/<int:course_id>/history')
@login_required
@instructor_required
def attendance_history(course_id):
    """
    Handles the attendance history functionality.
    Provides instructors with a list of past attendance submissions for a specific course.
    """
    # Verify course ownership
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    
    # Retrieve records sorted by attendance date in descending order
    records = Attendance.query.filter_by(course_id=course.id).order_by(Attendance.attendance_date.desc()).all()
    
    return render_template('attendance/attendance_history.html', course=course, records=records)