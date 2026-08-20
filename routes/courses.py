# Handles course creation, management, and enrollment.
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from utils.decorators import instructor_required, student_required
from models import Course, Enrollment, db, Category, Lesson, Video, StudyMaterial, Progress, Certificate
from urllib.parse import urlparse, parse_qs
from sqlalchemy import or_
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import time

courses_bp = Blueprint('courses', __name__, url_prefix='/courses')


def youtube_embed_url(url):
    if not url:
        return url

    if "youtube.com/embed/" in url:
        return url

    if "youtu.be/" in url:
        video_id = urlparse(url).path.strip("/")
        return f"https://www.youtube.com/embed/{video_id}"

    if "youtube.com/watch" in url:
        query = parse_qs(urlparse(url).query)
        video_id = query.get("v", [""])[0]
        if video_id:
            return f"https://www.youtube.com/embed/{video_id}"

    if "/shorts/" in url:
        video_id = url.split("/shorts/")[1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    return url


@courses_bp.route('/')
def list_courses():
    """List courses with optional filters."""
    query = Course.query

    selected_categories = request.args.getlist('category')
    if selected_categories:
        try:
            cat_ids = [int(c) for c in selected_categories]
            query = query.filter(Course.category_id.in_(cat_ids))
        except ValueError:
            query = query.join(Category).filter(Category.name.in_(selected_categories))

    selected_price = request.args.get('price', 'all')
    if selected_price == 'free':
        query = query.filter(or_(Course.price == 0, Course.price == None))
    elif selected_price == 'paid':
        query = query.filter(Course.price > 0)

    selected_instructors = request.args.getlist('instructor')
    if selected_instructors:
        try:
            inst_ids = [int(i) for i in selected_instructors]
            query = query.filter(Course.instructor_id.in_(inst_ids))
        except ValueError:
            pass

    courses = query.all()

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
    """Show course details page."""
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    if current_user.is_authenticated and current_user.role.name == 'student':
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course.id
        ).first()
        if enrollment:
            is_enrolled = True

    return render_template(
        'courses/course_details.html',
        course=course,
        is_enrolled=is_enrolled
    )


@courses_bp.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
@student_required
def enroll(course_id):
    """Enroll the current student in a course."""
    course = Course.query.get_or_404(course_id)

    existing = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course.id
    ).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.dashboard'))

    if getattr(course, 'course_type', None) == 'Paid' or (course.price or 0) > 0:
        return redirect(url_for('payment.checkout', course_id=course.id))

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
    """Create a new course."""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        course_type = request.form.get('course_type', 'Free')
        currency = request.form.get('currency', 'USD')
        price = request.form.get('price', 0.0)
        demo_video_title = request.form.get('demo_video_title')
        demo_video_url = request.form.get('demo_video_url')
        demo_video_file = request.files.get('demo_video_file')

        if demo_video_url:
            demo_video_url = youtube_embed_url(demo_video_url)

        if course_type == 'Free':
            price = 0.0

        final_demo_video_file = None
        if demo_video_file and demo_video_file.filename != '':
            filename = secure_filename(demo_video_file.filename)
            filename = f"{int(time.time())}_{filename}"
            demo_video_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            final_demo_video_file = f"/uploads/{filename}"

        new_course = Course(
            title=title,
            description=description,
            course_type=course_type,
            price=float(price) if price else 0.0,
            currency=currency,
            instructor_id=current_user.id,
            demo_video_title=demo_video_title,
            demo_video_url=demo_video_url,
            demo_video_file=final_demo_video_file
        )
        db.session.add(new_course)
        db.session.commit()

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
    """Update or delete a course's demo video."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

    action = request.form.get('action')

    if action == 'delete':
        course.demo_video_title = None
        course.demo_video_url = None
        course.demo_video_file = None
        db.session.commit()
        flash('Demo video deleted successfully!', 'success')
    else:
        demo_video_title = request.form.get('demo_video_title')
        demo_video_url = request.form.get('demo_video_url')
        demo_video_file = request.files.get('demo_video_file')

        if demo_video_url:
            demo_video_url = youtube_embed_url(demo_video_url)

        if demo_video_file and demo_video_file.filename != '':
            filename = secure_filename(demo_video_file.filename)
            filename = f"{int(time.time())}_{filename}"
            demo_video_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            course.demo_video_file = f"/uploads/{filename}"

        course.demo_video_title = demo_video_title
        course.demo_video_url = demo_video_url
        db.session.commit()
        flash('Demo video updated successfully!', 'success')

    return redirect(url_for('courses.manage_course', course_id=course.id))


@courses_bp.route('/<int:course_id>/manage', methods=['GET', 'POST'])
@login_required
@instructor_required
def manage_course(course_id):
    """Manage lessons and demo video of a course."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

    if request.method == 'POST' and request.form.get('action') == 'update_demo':
        demo_video_title = request.form.get('demo_video_title')
        demo_video_url = request.form.get('demo_video_url')

        if demo_video_url:
            demo_video_url = youtube_embed_url(demo_video_url)

        course.demo_video_title = demo_video_title
        course.demo_video_url = demo_video_url
        db.session.commit()
        flash('Demo video updated successfully!', 'success')
        return redirect(url_for('courses.manage_course', course_id=course.id))

    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    return render_template('courses/manage_course.html', course=course, lessons=lessons)


@courses_bp.route('/<int:course_id>/lessons/add', methods=['POST'])
@login_required
@instructor_required
def add_lesson(course_id):
    """Add a new lesson to a course."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

    title = request.form.get('title')
    content = request.form.get('content')
    video_url = request.form.get('video_url')
    video_file = request.files.get('video_file')

    max_order_lesson = Lesson.query.filter_by(course_id=course.id).order_by(
        Lesson.order_index.desc()
    ).first()
    new_order = (max_order_lesson.order_index + 1) if max_order_lesson else 1

    new_lesson = Lesson(
        course_id=course.id,
        title=title,
        description=content,
        order_index=new_order
    )
    db.session.add(new_lesson)
    db.session.flush()

    final_video_url = None
    if video_file and video_file.filename != '':
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

    from services.notification_service import send_notification
    enrollments = Enrollment.query.filter_by(course_id=course.id).all()
    for enrollment in enrollments:
        send_notification(
            user_id=enrollment.user_id,
            title="New Lesson Added",
            message=f"A new lesson '{title}' was added to {course.title}.",
            notification_type='info',
            icon='bi-journal-plus',
            action_url=f'/courses/{course.id}',
            sender_id=current_user.id
        )

    flash('Lesson added successfully!', 'success')
    return redirect(url_for('courses.manage_course', course_id=course.id))


@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/material/upload', methods=['POST'])
@login_required
@instructor_required
def upload_material(course_id, lesson_id):
    """Upload study material for a lesson."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()

    file = request.files.get('material_file')
    title = request.form.get('title')

    if file and file.filename != '':
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
    """Delete a study material."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

    material = StudyMaterial.query.filter_by(id=material_id, lesson_id=lesson_id).first_or_404()
    db.session.delete(material)
    db.session.commit()
    flash('Material deleted successfully!', 'success')
    return redirect(url_for('courses.manage_course', course_id=course.id))


@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/video/delete', methods=['POST'])
@login_required
@instructor_required
def delete_video(course_id, lesson_id):
    """Delete the video of a lesson."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

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
    """Add a video to an existing lesson."""
    course = Course.query.get_or_404(course_id)
    if course.instructor_id != current_user.id:
        flash('You can only manage your own courses.', 'error')
        return redirect(url_for('instructor.dashboard'))

    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()

    if lesson.video:
        flash('Lesson already has a video.', 'error')
        return redirect(url_for('courses.manage_course', course_id=course.id))

    video_url = request.form.get('video_url')
    video_file = request.files.get('video_file')

    final_video_url = None
    if video_file and video_file.filename != '':
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
    """View a single lesson."""
    course = Course.query.get_or_404(course_id)

    has_access = False
    if current_user.role.name == 'instructor' and course.instructor_id == current_user.id:
        has_access = True
    elif current_user.role.name == 'student':
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course.id
        ).first()
        if enrollment:
            has_access = True

    if not has_access:
        flash('You must be enrolled in this course to view its lessons.', 'error')
        return redirect(url_for('courses.course_details', course_id=course.id))

    from models import Result
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course.id).first_or_404()

    user_results = {}
    if current_user.is_authenticated and current_user.role.name == 'student':
        for quiz in lesson.quizzes:
            res = Result.query.filter_by(
                quiz_id=quiz.id, student_id=current_user.id
            ).order_by(Result.submitted_at.desc()).first()
            if res:
                user_results[quiz.id] = res

    all_lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()

    return render_template(
        'courses/lesson.html',
        course=course,
        lesson=lesson,
        all_lessons=all_lessons,
        user_results=user_results
    )


@courses_bp.route('/material/<int:material_id>/preview')
@login_required
def preview_material(material_id):
    """Preview a study material."""
    material = StudyMaterial.query.get_or_404(material_id)
    course = material.lesson.course

    has_access = False
    if current_user.role.name == 'instructor' and course.instructor_id == current_user.id:
        has_access = True
    elif current_user.role.name == 'student':
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course.id
        ).first()
        if enrollment:
            has_access = True

    if not has_access:
        flash('You do not have access to this material.', 'error')
        return redirect(url_for('index'))

    return render_template('courses/preview.html', material=material, course=course)


@courses_bp.route('/<int:course_id>/start', methods=['GET'])
@login_required
def course_start(course_id):
    """Redirect to the first lesson of a course."""
    course = Course.query.get_or_404(course_id)

    has_access = False
    if current_user.role.name == 'instructor' and course.instructor_id == current_user.id:
        has_access = True
    elif current_user.role.name == 'student':
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, course_id=course.id
        ).first()
        if enrollment:
            has_access = True

    if not has_access:
        flash('You must be enrolled to access this course.', 'error')
        return redirect(url_for('courses.course_details', course_id=course.id))

    first_lesson = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).first()

    if not first_lesson:
        flash('This course has no lessons yet. Please check back later!', 'info')
        return redirect(url_for('student.dashboard'))

    return redirect(url_for('courses.lesson_view', course_id=course.id, lesson_id=first_lesson.id))


@courses_bp.route('/<int:course_id>/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
@student_required
def complete_lesson(course_id, lesson_id):
    """Mark a lesson as complete and handle course completion + certificate."""
    from utils.certificate import generate_certificate
    from services.notification_service import send_notification
    from utils.email import send_certificate_email

    progress = Progress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if not progress:
        progress = Progress(
            user_id=current_user.id,
            lesson_id=lesson_id,
            completed=True,
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)
    else:
        progress.completed = True
        progress.completed_at = datetime.utcnow()

    db.session.commit()

    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course_id
    ).first()
    course_completed = False
    certificate_generated = False

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

            if old_percent < 100 and enrollment.progress_percent == 100:
                send_notification(
                    user_id=current_user.id,
                    title="Course Completed",
                    message=f"Congratulations! You have completed '{enrollment.course.title}'.",
                    notification_type='success',
                    icon='bi-mortarboard-fill',
                    action_url=f'/courses/{course_id}'
                )
                send_notification(
                    user_id=enrollment.course.instructor_id,
                    title="Course Completed",
                    message=f"{current_user.name} has completed '{enrollment.course.title}'.",
                    notification_type='info',
                    icon='bi-mortarboard-fill',
                    action_url='/instructor/students',
                    sender_id=current_user.id
                )

            if enrollment.progress_percent == 100:
                course_completed = True
                existing_cert = Certificate.query.filter_by(
                    student_id=current_user.id,
                    course_id=course_id
                ).first()

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
                    certificate_generated = True

                    send_notification(
                        user_id=student.id,
                        title="Certificate Sent to Your Email!",
                        message=f"Congratulations! Your certificate for '{course.title}' has been generated and sent to your email.",
                        notification_type='success',
                        icon='bi-award-fill',
                        action_url='/certificate/my_certificates'
                    )

                    try:
                        pdf_full_path = None
                        if file_path:
                            if file_path.startswith('/'):
                                pdf_full_path = os.path.join(current_app.root_path, file_path.lstrip('/'))
                            else:
                                pdf_full_path = os.path.join(
                                    current_app.config.get('UPLOAD_FOLDER', 'static/uploads'),
                                    file_path
                                )

                            if not os.path.exists(pdf_full_path):
                                possible_paths = [
                                    os.path.join(current_app.root_path, 'static', 'certificates', os.path.basename(file_path)),
                                    os.path.join(current_app.root_path, 'static', 'uploads', os.path.basename(file_path)),
                                    os.path.join(current_app.config.get('UPLOAD_FOLDER', ''), os.path.basename(file_path)),
                                    file_path
                                ]
                                for p in possible_paths:
                                    if os.path.exists(p):
                                        pdf_full_path = p
                                        break

                        download_url = url_for('certificate.my_certificates', _external=True)
                        completion_date = datetime.utcnow().strftime('%d %B %Y')

                        send_certificate_email(
                            recipient=student.email,
                            student_name=student.name,
                            course_title=course.title,
                            certificate_id=cert_id,
                            instructor_name=course.instructor.name if course.instructor else None,
                            completion_date=completion_date,
                            download_url=download_url,
                            pdf_path=pdf_full_path
                        )
                    except Exception as e:
                        print(f"Failed to send certificate email: {e}")

    current_lesson = Lesson.query.get_or_404(lesson_id)
    next_lesson = Lesson.query.filter(
        Lesson.course_id == course_id,
        Lesson.order_index > current_lesson.order_index
    ).order_by(Lesson.order_index).first()

    if certificate_generated:
        flash(
            '🎉 Congratulations! You have completed the course and your certificate has been sent to your email.',
            'success'
        )
        return redirect(url_for('student.dashboard'))
    elif course_completed:
        flash('🎉 Congratulations! You have completed all lessons in this course.', 'success')
        return redirect(url_for('student.dashboard'))
    else:
        flash('Lesson marked as complete!', 'success')
        if next_lesson:
            return redirect(url_for('courses.lesson_view', course_id=course_id, lesson_id=next_lesson.id))
        else:
            return redirect(url_for('student.dashboard'))