from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from utils.decorators import instructor_required
from models import db, Course, Lesson, Attendance, Enrollment, User
from datetime import datetime
# Handles attendance management for students and courses.
attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')

@attendance_bp.route('/course/<int:course_id>/manage', methods=['GET', 'POST'])
@login_required
@instructor_required
def manage_attendance(course_id):
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    
    # Sort students
    students = [e.student for e in enrollments]
    
    selected_date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
    selected_lesson_id = request.args.get('lesson_id', type=int)
    
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.utcnow().date()
        
    # Get existing attendance for this date and optional lesson
    query = Attendance.query.filter_by(course_id=course.id, attendance_date=selected_date)
    if selected_lesson_id:
        query = query.filter_by(lesson_id=selected_lesson_id)
        
    existing_records = query.all()
    attendance_dict = {record.student_id: record for record in existing_records}
    
    if request.method == 'POST':
        date_str = request.form.get('attendance_date')
        lesson_id = request.form.get('lesson_id', type=int)
        
        try:
            att_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            att_date = datetime.utcnow().date()
            
        for student in students:
            status = request.form.get(f'status_{student.id}')
            remarks = request.form.get(f'remarks_{student.id}')
            
            if status:
                # Check if record exists
                record_query = Attendance.query.filter_by(
                    course_id=course.id,
                    student_id=student.id,
                    attendance_date=att_date
                )
                if lesson_id:
                    record_query = record_query.filter_by(lesson_id=lesson_id)
                    
                record = record_query.first()
                
                if record:
                    record.status = status
                    record.remarks = remarks
                else:
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
                    
        db.session.commit()
        flash('Attendance saved successfully!', 'success')
        return redirect(url_for('attendance.manage_attendance', course_id=course.id, date=date_str, lesson_id=lesson_id))
        
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
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    records = Attendance.query.filter_by(course_id=course.id).order_by(Attendance.attendance_date.desc()).all()
    
    return render_template('attendance/attendance_history.html', course=course, records=records)
