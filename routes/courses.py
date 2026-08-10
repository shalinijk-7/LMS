# Handles course creation, management, and enrollment.
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Course
from models import Enrollment
from models import db
from urllib.parse import urlparse, parse_qs

def youtube_embed_url(url):
    if not url:
        return url

    # Already an embed URL
    if "youtube.com/embed/" in url:
        return url

    # https://youtu.be/VIDEO_ID
    if "youtu.be/" in url:
        video_id = urlparse(url).path.strip("/")
        return f"https://www.youtube.com/embed/{video_id}"

    # https://www.youtube.com/watch?v=VIDEO_ID
    if "youtube.com/watch" in url:
        query = parse_qs(urlparse(url).query)
        video_id = query.get("v", [""])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"

    # https://www.youtube.com/shorts/VIDEO_ID
    if "/shorts/" in url:
        video_id = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    return url

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

@courses_bp.route('/')
def list_courses():
    from models import Category, User
    from sqlalchemy import or_

    query = Course.query

    # Category filter
    selected_categories = request.args.getlist('category')
    if selected_categories:
        try:
            cat_ids = [int(c) for c in selected_categories]
            query = query.filter(Course.category_id.in_(cat_ids))
        except ValueError:
            query = query.join(Category).filter(Category.name.in_(selected_categories))

    # Price filter
    selected_price = request.args.get('price', 'all')
    if selected_price == 'free':
        query = query.filter(or_(Course.price == 0, Course.price == None))
    elif selected_price == 'paid':
        query = query.filter(Course.price > 0)

    # Instructor filter
    selected_instructors = request.args.getlist('instructor')
    if selected_instructors:
        try:
            inst_ids = [int(i) for i in selected_instructors]
            query = query.filter(Course.instructor_id.in_(inst_ids))
        except ValueError:
            pass

    courses = query.all()

    # All instructors for sidebar
    all_courses = Course.query.all()
    instructors = sorted(
        {course.instructor for course in all_courses if course.instructor},
        key=lambda u: u.name or ''
    )

    categories = Category.query.order_by(Category.name).all()

    return render_template(
        'courses/course_list.html',
        courses=courses,
        instructors=instructors,
        categories=categories,
        selected_categories=selected_categories,
        selected_price=selected_price,
        selected_instructors=selected_instructors
    )
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
    
    from services.notification_service import send_notification
    send_notification(
        user_id=course.instructor_id,
        title="New Student Enrollment",
        message=f"{current_user.name} just enrolled in '{course.title}'.",
        notification_type="info",
        icon="bi-person-plus-fill",
        action_url="/instructor/students"
    )
    
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
    video_file = request.files.get('video_file')
    
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
    
    final_video_url = None
    if video_file and video_file.filename != '':
        import os
        import time
        from werkzeug.utils import secure_filename
        from flask import current_app
        filename = secure_filename(video_file.filename)
        filename = f"{int(time.time())}_{filename}"
        video_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        final_video_url = f"/uploads/{filename}"
    elif video_url:
        final_video_url = youtube_embed_url(video_url)
        
    if final_video_url:
        new_video = Video(lesson_id=new_lesson.id, url=final_video_url)
        db.session.add(new_video)
        
    db.session.commit()
    
    # Send notification to all enrolled students
    from models import Enrollment
    from services.notification_service import send_notification
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    for enrollment in enrollments:
        send_notification(
            user_id=enrollment.user_id,
            title="New Lesson Added",
            message=f"A new lesson '{title}' was added to {course.title}.",
            notification_type='info',
            icon='bi-journal-plus',
            action_url=f'/course/{course.id}',
            sender_id=current_user.id
        )
    db.session.commit()
    
    flash('Lesson added successfully!', 'success')
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/material/upload', methods=['POST'])
@login_required
def upload_material(course_id, lesson_id):
    if current_user.role.name != 'instructor':
        flash('Only instructors can upload materials.', 'error')
        return redirect(url_for('student.dashboard'))
        
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    from models import Lesson, StudyMaterial
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    file = request.files.get('material_file')
    title = request.form.get('title')
    
    if file and file.filename != '':
        import os
        import time
        from werkzeug.utils import secure_filename
        from flask import current_app
        
        filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        new_material = StudyMaterial(
            lesson_id=lesson.id,
            title=title or file.filename,
            file_path=f"/uploads/{filename}",
            file_type=file_ext
        )
        db.session.add(new_material)
        db.session.commit()
        flash('Study material uploaded successfully!', 'success')
    else:
        flash('No file selected.', 'error')
        
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/material/<int:material_id>/delete', methods=['POST'])
@login_required
def delete_material(course_id, lesson_id, material_id):
    if current_user.role.name != 'instructor':
        flash('Only instructors can manage materials.', 'error')
        return redirect(url_for('student.dashboard'))
        
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    from models import StudyMaterial
    material = StudyMaterial.query.filter_by(id=material_id, lesson_id=lesson_id).first_or_404()
    
    db.session.delete(material)
    db.session.commit()
    flash('Material deleted successfully!', 'success')
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/video/delete', methods=['POST'])
@login_required
def delete_video(course_id, lesson_id):
    if current_user.role.name != 'instructor':
        flash('Only instructors can manage materials.', 'error')
        return redirect(url_for('student.dashboard'))
        
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    from models import Lesson, Video
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    if lesson.video:
        db.session.delete(lesson.video)
        db.session.commit()
        flash('Video deleted successfully!', 'success')
        
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/video/add', methods=['POST'])
@login_required
def add_lesson_video(course_id, lesson_id):
    if current_user.role.name != 'instructor':
        flash('Only instructors can manage materials.', 'error')
        return redirect(url_for('student.dashboard'))
        
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    from models import Lesson, Video
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    if lesson.video:
        flash('Lesson already has a video.', 'error')
        return redirect(url_for('courses.manage_course', course_id=course.id))
        
    video_url = request.form.get('video_url')
    video_file = request.files.get('video_file')
    
    final_video_url = None
    if video_file and video_file.filename != '':
        import os
        import time
        from werkzeug.utils import secure_filename
        from flask import current_app
        filename = secure_filename(video_file.filename)
        filename = f"{int(time.time())}_{filename}"
        video_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        final_video_url = f"/uploads/{filename}"
    elif video_url:
       final_video_url = youtube_embed_url(video_url)
        
    if final_video_url:
        new_video = Video(lesson_id=lesson.id, url=final_video_url)
        db.session.add(new_video)
        db.session.commit()
        flash('Video added successfully!', 'success')
    else:
        flash('No video link or file provided.', 'error')
        
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
        
    from models import Lesson, Result
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    # Fetch user results for any quizzes attached to this lesson
    user_results = {}
    if current_user.is_authenticated and current_user.role.name == 'student':
        for quiz in lesson.quizzes:
            res = Result.query.filter_by(quiz_id=quiz.id, student_id=current_user.id).order_by(Result.submitted_at.desc()).first()
            if res:
                user_results[quiz.id] = res
    
    # Get all lessons for navigation sidebar
    all_lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    return render_template('courses/lesson.html', course=course, lesson=lesson, all_lessons=all_lessons, user_results=user_results)

@courses_bp.route('/material/<int:material_id>/preview')
@login_required
def preview_material(material_id):
    from models import StudyMaterial
    material = StudyMaterial.query.get_or_404(material_id)
    
    # Check if the user is enrolled or is the instructor
    course = material.lesson.course
    has_access = False
    
    if current_user.role.name == 'instructor' and course.instructor_id == current_user.id:
        has_access = True
    elif current_user.role.name == 'student':
        from models import Enrollment
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if enrollment:
            has_access = True
            
    if not has_access:
        flash('You do not have access to this material.', 'error')
        return redirect(url_for('main.index'))
        
    return render_template('courses/preview.html', material=material, course=course)

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
    from models import Enrollment, Lesson, Certificate
    from utils.certificate import generate_certificate
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
            
            # Check if course is completed and generate certificate if not already present
            if enrollment.progress_percent == 100:
                existing_cert = Certificate.query.filter_by(student_id=current_user.id, course_id=course_id).first()
                if not existing_cert:
                    # Generate certificate
                    course = enrollment.course
                    student = current_user
                    cert_id, file_path = generate_certificate(student.name, course.title)
                    
                    new_cert = Certificate(
                        student_id=student.id,
                        course_id=course.id,
                        certificate_id=cert_id,
                        file_path=file_path
                    )
                    db.session.add(new_cert)
                    
                    from services.notification_service import send_notification
                    send_notification(
                        user_id=student.id,
                        title="Certificate Generated",
                        message=f"Your certificate for {course.title} is ready!",
                        notification_type='success',
                        icon='bi-award-fill',
                        action_url='/certificate/my_certificates'
                    )
                    
                    db.session.commit()
                    flash(f'Congratulations! You have earned a certificate for completing {course.title}.', 'success')
    
    # Try to find the next lesson
    current_lesson = Lesson.query.get_or_404(lesson_id)
    next_lesson = Lesson.query.filter(Lesson.course_id == course_id, Lesson.order_index > current_lesson.order_index).order_by(Lesson.order_index).first()
    
    flash('Lesson marked as complete!', 'success')
    
    if next_lesson:
        return redirect(url_for('courses.lesson_view', course_id=course_id, lesson_id=next_lesson.id))
    else:
        flash('Congratulations! You have completed all lessons in this course.', 'success')
        return redirect(url_for('student.dashboard'))
