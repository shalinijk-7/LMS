from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from utils.decorators import instructor_required, student_required
from models import Course
from models import Enrollment
from models import db

# Define the blueprint for all course-related routes
courses_bp = Blueprint('courses', __name__, url_prefix='/courses')

@courses_bp.route('/')
def list_courses():
    """
    Route to display a list of all available courses.
    Retrieves all available courses and extracts unique instructors and categories for filtering.
    """
    courses = Course.query.all()
    # Get unique instructors from the available courses
    instructors = {course.instructor for course in courses if course.instructor}
    # Get unique categories from the available courses
    categories = {course.category.name for course in courses if course.category}
    return render_template('courses/course_list.html', courses=courses, instructors=instructors, categories=categories)

@courses_bp.route('/<int:course_id>')
def course_details(course_id):
    """
    Route to display details for a specific course.
    Fetches details for a specific course and checks if the currently logged-in student is enrolled.
    """
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    
    # Check enrollment status for logged-in students
    if current_user.is_authenticated and current_user.role.name == 'student':
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if enrollment:
            is_enrolled = True
            
    return render_template('courses/course_details.html', course=course, is_enrolled=is_enrolled)

@courses_bp.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
@student_required
def enroll(course_id):
    """
    Route to handle student enrollment in a course.
    Validates enrollment eligibility, processes payments for paid courses,
    and creates enrollment records for free courses.
    Notifies both the student and the instructor upon successful enrollment.
    """
    course = Course.query.get_or_404(course_id)
    
    # Prevent duplicate enrollments
    existing = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.dashboard'))
        
    # Redirect to checkout if the course is paid
    if course.course_type == 'Paid':
        return redirect(url_for('payment.checkout', course_id=course.id))
        
    # Handle free course enrollment instantly
    new_enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
    db.session.add(new_enrollment)
    db.session.commit()
    
    # Send real-time notifications to the instructor and the enrolling student
    from services.notification_service import send_notification
    send_notification(
        user_id=course.instructor_id,
        title="New Student Enrollment",
        message=f"{current_user.name} just enrolled in '{course.title}'.",
        notification_type="info",
        icon="bi-person-plus-fill",
        action_url="/instructor/students"
    )
    
    send_notification(
        user_id=current_user.id,
        title="Enrollment Successful",
        message=f"You have successfully enrolled in '{course.title}'.",
        notification_type="success",
        icon="bi-check-circle-fill",
        action_url=f"/courses/{course.id}/start"
    )
    
    flash(f'Successfully enrolled in {course.title}!', 'success')
    return redirect(url_for('student.dashboard'))

@courses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_course():
    """
    Route for instructors to create a new course.
    Allows authorized instructors to create a new course with optional demo video uploads.
    Handles file uploading and notifies administrators of the new course.
    """
    if request.method == 'POST':
        # Retrieve form parameters
        title = request.form.get('title')
        description = request.form.get('description')
        course_type = request.form.get('course_type', 'Free')
        currency = request.form.get('currency', 'USD')
        price = request.form.get('price', 0.0)
        
        demo_video_title = request.form.get('demo_video_title')
        demo_video_url = request.form.get('demo_video_url')
        demo_video_file = request.files.get('demo_video_file')
        
        # Enforce zero price for free courses
        if course_type == 'Free':
            price = 0.0
            
        # Securely saveuploaded demo video file if present
        final_demo_video_file = None
        if demo_video_file and demo_video_file.filename != '':
            import os
            import time
            from werkzeug.utils import secure_filename
            from flask import current_app
            filename = secure_filename(demo_video_file.filename)
            filename = f"{int(time.time())}_{filename}"
            demo_video_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            final_demo_video_file = f"/uploads/{filename}"
        
        # Create and persist the course record
        new_course = Course(
            title=title,
            description=description,
            course_type=course_type,
            price=float(price),
            currency=currency,
            instructor_id=current_user.id,
            demo_video_title=demo_video_title,
            demo_video_url=demo_video_url,
            demo_video_file=final_demo_video_file
        )
        db.session.add(new_course)
        db.session.commit()
        
        # Notify administration about the new course creation
        from services.notification_service import notify_admins
        notify_admins(
            title="New Course Created",
            message=f"Instructor {current_user.name} created a new course '{title}'.",
            notification_type='info',
            icon='bi-journal-plus',
            action_url='/admin/courses'
        )
        
        flash('Course created successfully!', 'success')
        return redirect(url_for('instructor.dashboard'))
        
    return render_template('courses/create_course.html')

@courses_bp.route('/<int:course_id>/demo_video/update', methods=['POST'])
@login_required
@instructor_required
def update_demo_video(course_id):
    """
    Route to update or delete a course's demo video.
    Allows instructors to update or completely remove their course's promotional video assets.
    """
    course = Course.query.get_or_404(course_id)
    # Authorization check
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    action = request.form.get('action')
    
    # Process video deletion
    if action == 'delete':
        course.demo_video_title = None
        course.demo_video_url = None
        course.demo_video_file = None
        db.session.commit()
        flash('Demo video deleted successfully!', 'success')
    # Process video modification
    else:
        demo_video_title = request.form.get('demo_video_title')
        demo_video_url = request.form.get('demo_video_url')
        demo_video_file = request.files.get('demo_video_file')
        
        # Save new upload if provided
        if demo_video_file and demo_video_file.filename != '':
            import os
            import time
            from werkzeug.utils import secure_filename
            from flask import current_app
            filename = secure_filename(demo_video_file.filename)
            filename = f"{int(time.time())}_{filename}"
            demo_video_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            course.demo_video_file = f"/uploads/{filename}"
            
        course.demo_video_title = demo_video_title
        course.demo_video_url = demo_video_url
        db.session.commit()
        flash('Demo video updated successfully!', 'success')
        
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/manage', methods=['GET'])
@login_required
@instructor_required
def manage_course(course_id):
    """
    Route to render the course management dashboard for instructors.
    Renders the management dashboard for a specific course, displaying its curriculum.
    """
    course = Course.query.get_or_404(course_id)
    # Verify course ownership
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    from models import Lesson
    # Retrieve curriculum lessons ordered sequentially
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    return render_template('courses/manage_course.html', course=course, lessons=lessons)

@courses_bp.route('/<int:course_id>/lessons/add', methods=['POST'])
@login_required
@instructor_required
def add_lesson(course_id):
    """
    Route to add a new lesson to a course.
    Appends a new lesson to the end of the course timeline, handles associated media,
    and notifies all enrolled participants.
    """
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    title = request.form.get('title')
    content = request.form.get('content')
    video_url = request.form.get('video_url')
    video_file = request.files.get('video_file')
    
    from models import Lesson, Video
    # Calculate the sequential order index for the new lesson
    max_order_lesson = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index.desc()).first()
    new_order = (max_order_lesson.order_index + 1) if max_order_lesson else 1
    
    new_lesson = Lesson(
        course_id=course.id,
        title=title,
        description=content,
        order_index=new_order
    )
    db.session.add(new_lesson)
    db.session.flush() # Flush to populate ID for video association
    
    # Process video asset priority (uploaded file overrides raw URL)
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
        final_video_url = video_url
        
    if final_video_url:
        new_video = Video(lesson_id=new_lesson.id, url=final_video_url)
        db.session.add(new_video)
        
    db.session.commit()
    
    # Notify all enrolled students regarding newly updated course material
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
@instructor_required
def upload_material(course_id, lesson_id):
    """
    Route to upload supplementary study materials for a lesson.
    Processes supplemental study resource attachments for a specific lesson and updates students.
    """
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
        
        # Generate unique filename on disk
        filename = secure_filename(file.filename)
        filename = f"{int(time.time())}_{filename}"
        file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
        
        # Track file extensions for display purposes
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        new_material = StudyMaterial(
            lesson_id=lesson.id,
            title=title or file.filename,
            file_path=f"/uploads/{filename}",
            file_type=file_ext
        )
        db.session.add(new_material)
        db.session.commit()
        
        # Broadcast material update notification to students
        from models import Enrollment
        from services.notification_service import send_notification
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            send_notification(
                user_id=enrollment.user_id,
                title="New Study Material",
                message=f"New material '{title or file.filename}' added to {course.title}.",
                notification_type='info',
                icon='bi-file-earmark-text',
                action_url=f'/courses/{course.id}/lesson/{lesson.id}',
                sender_id=current_user.id
            )
            
        flash('Study material uploaded successfully!', 'success')
    else:
        flash('No file selected.', 'error')
        
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/material/<int:material_id>/delete', methods=['POST'])
@login_required
@instructor_required
def delete_material(course_id, lesson_id, material_id):
    """
    Route to delete a study material from a lesson.
    Removes a study resource attachment permanently from the database.
    """
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
@instructor_required
def delete_video(course_id, lesson_id):
    """
    Route to delete a lesson's associated video.
    Removes a lesson's associated video lecture structure.
    """
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
@instructor_required
def add_lesson_video(course_id, lesson_id):
    """
    Route to add a video to a lesson.
    Attaches a video resource to an existing lesson if it does not already contain one.
    """
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))
        
    from models import Lesson, Video
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()
    
    # Enforce one-video-per-lesson validation constraint
    if lesson.video:
        flash('Lesson already has a video.', 'error')
        return redirect(url_for('courses.manage_course', course_id=course.id))
        
    video_url = request.form.get('video_url')
    video_file = request.files.get('video_file')
    
    # Process the provided video input method
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
        final_video_url = video_url
        
    if final_video_url:
        new_video = Video(lesson_id=lesson.id, url=final_video_url)
        db.session.add(new_video)
        db.session.commit()
        
        # Broadcast video upload notification to students
        from models import Enrollment
        from services.notification_service import send_notification
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            send_notification(
                user_id=enrollment.user_id,
                title="New Video Added",
                message=f"A new video was added to '{lesson.title}' in {course.title}.",
                notification_type='info',
                icon='bi-play-btn-fill',
                action_url=f'/courses/{course.id}/lesson/{lesson.id}',
                sender_id=current_user.id
            )
            
        flash('Video added successfully!', 'success')
    else:
        flash('No video link or file provided.', 'error')
        
    return redirect(url_for('courses.manage_course', course_id=course.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>', methods=['GET'])
@login_required
def lesson_view(course_id, lesson_id):
    """
    Route to view a specific lesson's content.
    Validates user credentials (instructor ownership or active enrollment) before rendering course contents.
    Retrieves the lesson details, student quiz results, and the course curriculum.
    """
    course = Course.query.get_or_404(course_id)
    
    # Access security check
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
    
    # Retrieve any completed student quiz results to display in the UI sidebar/view
    user_results = {}
    if current_user.is_authenticated and current_user.role.name == 'student':
        for quiz in lesson.quizzes:
            res = Result.query.filter_by(quiz_id=quiz.id, student_id=current_user.id).order_by(Result.submitted_at.desc()).first()
            if res:
                user_results[quiz.id] = res
    
    # Get all course lessons for sequential navigation index
    all_lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    return render_template('courses/lesson.html', course=course, lesson=lesson, all_lessons=all_lessons, user_results=user_results)

@courses_bp.route('/material/<int:material_id>/preview')
@login_required
def preview_material(material_id):
    """
    Route to preview a study material.
    Displays course attachments in a sandboxed view for authorized users.
    """
    from models import StudyMaterial
    material = StudyMaterial.query.get_or_404(material_id)
    
    # Access security check
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
    """
    Route to initiate a course for a student.
    Locates the entry point (first lesson by sequence index) and redirects the user.
    """
    course = Course.query.get_or_404(course_id)
    
    # Access security check
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
    
    # Redirect gracefully if course is currently empty
    if not first_lesson:
        flash('This course has no lessons yet. Please check back later!', 'info')
        return redirect(url_for('student.dashboard'))
        
    return redirect(url_for('courses.lesson_view', course_id=course.id, lesson_id=first_lesson.id))

@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
@student_required
def complete_lesson(course_id, lesson_id):
    """
    Route to mark a lesson as complete for a student.
    Updates progress logs, recalculates completion metrics, awards dynamic PDF certificates
    upon crossing the 100% threshold, and routes students to the next chronological lesson.
    """
    from models import Progress
    from datetime import datetime
    
    # Record or update lesson completion status
    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, lesson_id=lesson_id, completed=True, completed_at=datetime.utcnow())
        db.session.add(progress)
    else:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
        
    db.session.commit()
    
    # Recalculate course enrollment progress percentage
    from models import Enrollment, Lesson, Certificate
    from utils.certificate import generate_certificate
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        total_lessons = Lesson.query.filter_by(course_id=course_id).count()
        if total_lessons > 0:
            old_percent = enrollment.progress_percent or 0
            
            completed_lessons = Progress.query.join(Lesson).filter(
                Progress.user_id == current_user.id,
                Lesson.course_id == course_id,
                Progress.completed == True
            ).count()
            enrollment.progress_percent = int((completed_lessons / total_lessons) * 100)
            db.session.commit()
            
            # Send notifications once completion metrics hit 100%
            if old_percent < 100 and enrollment.progress_percent == 100:
                from services.notification_service import send_notification
                
                # Notify Student
                send_notification(
                    user_id=current_user.id,
                    title="Course Completed",
                    message=f"Congratulations! You have completed '{enrollment.course.title}'.",
                    notification_type='success',
                    icon='bi-mortarboard-fill',
                    action_url=f'/courses/{course_id}'
                )
                
                # Notify Instructor
                send_notification(
                    user_id=enrollment.course.instructor_id,
                    title="Course Completed",
                    message=f"{current_user.name} has completed '{enrollment.course.title}'.",
                    notification_type='info',
                    icon='bi-mortarboard-fill',
                    action_url=f'/instructor/students',
                    sender_id=current_user.id
                )
            
            # Trigger unique PDF certificate generation on 100% course status
            if enrollment.progress_percent == 100:
                existing_cert = Certificate.query.filter_by(student_id=current_user.id, course_id=course_id).first()
                if not existing_cert:
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
                    db.session.commit()
                    
                    # Deliver generated certificate via Email service
                    from services.email_service import send_certificate_email
                    from datetime import datetime
                    email_success = send_certificate_email(student, course, file_path)
                    
                    if email_success:
                        new_cert.email_sent = True
                        new_cert.email_sent_at = datetime.utcnow()
                        db.session.commit()
                        
                    # Issue dashboard alert for the certificate
                    from services.notification_service import send_notification
                    send_notification(
                        user_id=student.id,
                        title="Certificate Generated",
                        message=f"Your certificate for {course.title} is ready!",
                        notification_type='success',
                        icon='bi-award-fill',
                        action_url='/certificate/my_certificates'
                    )
                    
                    flash(f'Congratulations! You have earned a certificate for completing {course.title}.', 'success')
    
    # Determine next chronological lesson routing
    current_lesson = Lesson.query.get_or_404(lesson_id)
    next_lesson = Lesson.query.filter(Lesson.course_id == course_id, Lesson.order_index > current_lesson.order_index).order_by(Lesson.order_index).first()
    
    flash('Lesson marked as complete!', 'success')
    
    if next_lesson:
        return redirect(url_for('courses.lesson_view', course_id=course_id, lesson_id=next_lesson.id))
    else:
        flash('Congratulations! You have completed all lessons in this course.', 'success')
        return redirect(url_for('student.dashboard'))