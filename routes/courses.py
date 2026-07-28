from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Course
from models import Enrollment
from models import db

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

@courses_bp.route('/')
def list_courses():
    courses = Course.query.all()
    return render_template('courses/course_list.html', courses=courses)

@courses_bp.route('/<int:course_id>')
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    if current_user.is_authenticated and current_user.role == 'student':
        enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course.id).first()
        if enrollment:
            is_enrolled = True
            
    return render_template('courses/course_details.html', course=course, is_enrolled=is_enrolled)

@courses_bp.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    if current_user.role != 'student':
        flash('Only students can enroll in courses.', 'error')
        return redirect(url_for('courses.course_details', course_id=course_id))
        
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(student_id=current_user.id, course_id=course.id).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('dashboard.index'))
        
    new_enrollment = Enrollment(student_id=current_user.id, course_id=course.id)
    db.session.add(new_enrollment)
    db.session.commit()
    
    flash(f'Successfully enrolled in {course.title}!', 'success')
    return redirect(url_for('dashboard.index'))

@courses_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role != 'instructor':
        flash('Only instructors can create courses.', 'error')
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        price = request.form.get('price', 0.0)
        
        new_course = Course(
            title=title,
            description=description,
            price=float(price),
            instructor_id=current_user.id
        )
        db.session.add(new_course)
        db.session.commit()
        
        flash('Course created successfully!', 'success')
        return redirect(url_for('dashboard.index'))
        
    return render_template('courses/create_course.html')
