from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Course
from models import Enrollment
from models import db

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

@courses_bp.route('/')
def list_courses():
    courses = Course.query.all()
    # Get unique instructors from the available courses
    instructors = {course.instructor for course in courses if course.instructor}
    return render_template('courses/course_list.html', courses=courses, instructors=instructors)

@courses_bp.route('/<int:course_id>')
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    if current_user.is_authenticated and current_user.role.name == 'student':
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if enrollment:
            is_enrolled = True
            
    return render_template('courses/course_details.html', course=course, is_enrolled=is_enrolled)

@courses_bp.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll(course_id):
    if current_user.role.name != 'student':
        flash('Only students can enroll in courses.', 'error')
        return redirect(url_for('courses.course_details', course_id=course_id))
        
    course = Course.query.get_or_404(course_id)
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.dashboard'))
        
    new_enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
    db.session.add(new_enrollment)
    db.session.commit()
    
    flash(f'Successfully enrolled in {course.title}!', 'success')
    return redirect(url_for('student.dashboard'))

@courses_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_course():
    if current_user.role.name != 'instructor':
        flash('Only instructors can create courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
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
        return redirect(url_for('instructor.dashboard'))
        
    return render_template('courses/create_course.html')

@courses_bp.route('/<int:course_id>/manage', methods=['GET'])
@login_required
def manage_course(course_id):
    if current_user.role.name != 'instructor':
        flash('Only instructors can manage courses.', 'error')
        return redirect(url_for('student.dashboard'))
        
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    # We will need the Lesson model to fetch lessons here
    from models import Lesson
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    return render_template('courses/manage_course.html', course=course, lessons=lessons)

@courses_bp.route('/<int:course_id>/lessons/add', methods=['POST'])
@login_required
def add_lesson(course_id):
    if current_user.role.name != 'instructor':
        flash('Only instructors can add lessons.', 'error')
        return redirect(url_for('student.dashboard'))
        
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    title = request.form.get('title')
    content = request.form.get('content')
    video_url = request.form.get('video_url')
    
    from models import Lesson, Video
    # Get current max order
    max_order_lesson = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index.desc()).first()
    new_order = (max_order_lesson.order_index + 1) if max_order_lesson else 1
    
    new_lesson = Lesson(
        course_id=course.id,
        title=title,
        description=content,
        order_index=new_order
    )
    db.session.add(new_lesson)
    db.session.flush() # get new_lesson.id
    
    if video_url:
        new_video = Video(lesson_id=new_lesson.id, url=video_url)
        db.session.add(new_video)
        
    db.session.commit()
    
    # Send notification to all enrolled students
    from models import Enrollment, Notification
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    for enrollment in enrollments:
        notif = Notification(
            user_id=enrollment.user_id,
            title="New Lesson Added",
            message=f"A new lesson '{title}' was added to {course.title}."
        )
        db.session.add(notif)
    db.session.commit()
    
    flash('Lesson added successfully!', 'success')
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>', methods=['GET'])
@login_required
def lesson_view(course_id, lesson_id):
    course = Course.query.get_or_404(course_id)
    
    # Check if student is enrolled (or if they are the instructor of the course)
    has_access = False
    if current_user.role.name == 'instructor' and course.instructor_id == current_user.id:
        has_access = True
    elif current_user.role.name == 'student':
        from models import Enrollment
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if enrollment:
            has_access = True
            
    if not has_access:
        flash('You must be enrolled in this course to view its lessons.', 'error')
        return redirect(url_for('courses.course_details', course_id=course.id))
        
    from models import Lesson
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    # Get all lessons for navigation sidebar
    all_lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    return render_template('courses/lesson.html', course=course, lesson=lesson, all_lessons=all_lessons)

@courses_bp.route('/<int:course_id>/start', methods=['GET'])
@login_required
def course_start(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Verify enrollment or instructor status
    has_access = False
    if current_user.role.name == 'instructor' and course.instructor_id == current_user.id:
        has_access = True
    elif current_user.role.name == 'student':
        from models import Enrollment
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if enrollment:
            has_access = True
            
    if not has_access:
        flash('You must be enrolled to access this course.', 'error')
        return redirect(url_for('courses.course_details', course_id=course.id))
        
    from models import Lesson
    first_lesson = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).first()
    
    if not first_lesson:
        flash('This course has no lessons yet. Please check back later!', 'info')
        return redirect(url_for('student.dashboard'))
        
    return redirect(url_for('courses.lesson_view', course_id=course.id, lesson_id=first_lesson.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(course_id, lesson_id):
    if current_user.role.name != 'student':
        flash('Only students can complete lessons.', 'error')
        return redirect(url_for('courses.lesson_view', course_id=course_id, lesson_id=lesson_id))
    
    from models import Progress
    from datetime import datetime
    
    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, lesson_id=lesson_id, completed=True, completed_at=datetime.utcnow())
        db.session.add(progress)
    else:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        
    db.session.commit()
    
    # Update course enrollment progress_percent
    from models import Enrollment, Lesson
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        total_lessons = Lesson.query.filter_by(course_id=course_id).count()
        if total_lessons > 0:
            completed_lessons = Progress.query.join(Lesson).filter(
                Progress.user_id == current_user.id,
                Lesson.course_id == course_id,
                Progress.completed == True
            ).count()
            enrollment.progress_percent = int((completed_lessons / total_lessons) * 100)
            db.session.commit()
    
    # Try to find the next lesson
    current_lesson = Lesson.query.get_or_404(lesson_id)
    next_lesson = Lesson.query.filter(Lesson.course_id == course_id, Lesson.order_index > current_lesson.order_index).order_by(Lesson.order_index).first()
    
    flash('Lesson marked as complete!', 'success')
    
    if next_lesson:
        return redirect(url_for('courses.lesson_view', course_id=course_id, lesson_id=next_lesson.id))
    else:
        flash('Congratulations! You have completed all lessons in this course.', 'success')
        return redirect(url_for('student.dashboard'))
