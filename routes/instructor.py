from flask import Blueprint, render_template
from flask_login import login_required, current_user
from utils.decorators import instructor_required
from models import db, Course

instructor_bp = Blueprint('instructor', __name__, url_prefix='/instructor')

@instructor_bp.route('/dashboard')
@login_required
@instructor_required
def dashboard():
    """
    Route to render the instructor's dashboard.
    Calculates total students, revenue, and course completion rates to display analytics.
    """
    from models import CourseCompletion, Enrollment, Payment
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    total_students = sum(len(course.enrollments) for course in courses)
    
    total_revenue = 0
    for course in courses:
        payments = Payment.query.filter_by(course_id=course.id, status='Success').all()
        total_revenue += sum(p.amount for p in payments)
    
    course_data = []
    for course in courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        # Count completion if progress is 100 or if CourseCompletion record exists
        completions = sum(1 for e in enrollments if e.progress_percent == 100 or CourseCompletion.query.filter_by(student_id=e.user_id, course_id=course.id).first())
        completion_rate = int((completions / len(enrollments)) * 100) if enrollments else 0
        course_data.append({
            'course': course,
            'completion_rate': completion_rate
        })
    
    return render_template('dashboard/instructor_dashboard.html', 
                           courses=courses,
                           course_data=course_data,
                           total_students=total_students, 
                           total_revenue=total_revenue)

@instructor_bp.route('/sales')
@login_required
@instructor_required
def sales():
    """
    Route to display the instructor's sales and process refunds.
    """
    from models import Payment, Course
    # Get payments for courses owned by this instructor
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    course_ids = [c.id for c in courses]
    
    payments = Payment.query.filter(Payment.course_id.in_(course_ids)).order_by(Payment.payment_date.desc()).all()
    
    return render_template('dashboard/instructor_sales.html', payments=payments)

@instructor_bp.route('/coupons')
@login_required
@instructor_required
def coupons():
    from flask import request, flash, redirect, url_for, jsonify
    from models import Coupon
    coupons = Coupon.query.filter_by(instructor_id=current_user.id).order_by(Coupon.created_at.desc()).all()
    return render_template('dashboard/instructor_coupons.html', coupons=coupons)

@instructor_bp.route('/coupons/create', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_coupon():
    from flask import request, flash, redirect, url_for, jsonify
    from models import Coupon, Course
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        discount_type = request.form.get('discount_type', 'percentage')
        discount_value = request.form.get('discount_value', type=float)
        course_id = request.form.get('course_id')
        usage_limit = request.form.get('usage_limit', type=int)
        min_purchase = request.form.get('min_purchase_amount', type=float)
        expiry_date_str = request.form.get('expiry_date')
        
        if not code or discount_value is None:
            flash('Code and discount value are required.', 'error')
            return redirect(request.url)
            
        existing = Coupon.query.filter_by(code=code).first()
        if existing:
            flash('Coupon code already exists.', 'error')
            return redirect(request.url)
            
        from datetime import datetime
        expiry_date = None
        if expiry_date_str:
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%dT%H:%M')
            
        coupon = Coupon(
            code=code,
            discount_type=discount_type,
            discount_percentage=discount_value if discount_type == 'percentage' else None,
            discount_fixed_amount=discount_value if discount_type == 'fixed' else None,
            course_id=int(course_id) if course_id and course_id != 'all' else None,
            instructor_id=current_user.id,
            usage_limit=usage_limit if usage_limit else None,
            min_purchase_amount=min_purchase if min_purchase else None,
            expiry_date=expiry_date,
            is_active=True
        )
        db.session.add(coupon)
        db.session.commit()
        flash('Coupon created successfully.', 'success')
        return redirect(url_for('instructor.coupons'))
        
    return render_template('dashboard/instructor_coupon_form.html', courses=courses, coupon=None)

@instructor_bp.route('/coupons/edit/<int:coupon_id>', methods=['GET', 'POST'])
@login_required
@instructor_required
def edit_coupon(coupon_id):
    from flask import request, flash, redirect, url_for, jsonify
    from models import Coupon, Course
    coupon = Coupon.query.get_or_404(coupon_id)
    if coupon.instructor_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('instructor.coupons'))
        
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    if request.method == 'POST':
        coupon.discount_type = request.form.get('discount_type', 'percentage')
        discount_value = request.form.get('discount_value', type=float)
        if coupon.discount_type == 'percentage':
            coupon.discount_percentage = discount_value
            coupon.discount_fixed_amount = None
        else:
            coupon.discount_fixed_amount = discount_value
            coupon.discount_percentage = None
            
        course_id = request.form.get('course_id')
        coupon.course_id = int(course_id) if course_id and course_id != 'all' else None
        
        usage_limit = request.form.get('usage_limit', type=int)
        coupon.usage_limit = usage_limit if usage_limit else None
        
        min_purchase = request.form.get('min_purchase_amount', type=float)
        coupon.min_purchase_amount = min_purchase if min_purchase else None
        
        expiry_date_str = request.form.get('expiry_date')
        from datetime import datetime
        if expiry_date_str:
            coupon.expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%dT%H:%M')
        else:
            coupon.expiry_date = None
            
        db.session.commit()
        flash('Coupon updated successfully.', 'success')
        return redirect(url_for('instructor.coupons'))
        
    return render_template('dashboard/instructor_coupon_form.html', courses=courses, coupon=coupon)

@instructor_bp.route('/coupons/toggle/<int:coupon_id>', methods=['POST'])
@login_required
@instructor_required
def toggle_coupon(coupon_id):
    from flask import request, flash, redirect, url_for, jsonify
    from models import Coupon
    coupon = Coupon.query.get_or_404(coupon_id)
    if coupon.instructor_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'})
        
    coupon.is_active = not coupon.is_active
    db.session.commit()
    flash(f"Coupon {'activated' if coupon.is_active else 'deactivated'}.", 'success')
    return redirect(url_for('instructor.coupons'))

@instructor_bp.route('/students')
@login_required
@instructor_required
def students():
    """
    Route to list students enrolled in the instructor's courses.
    Allows filtering by progress (completed, in progress, not started) and displays completion status.
    """
    from flask import request
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    # Sort courses so that courses with enrollments appear first
    courses.sort(key=lambda c: len(c.enrollments), reverse=True)
    course_ids = [c.id for c in courses]
    
    from models import Enrollment, User, CourseCompletion
    # Get all enrollments for the instructor's courses
    enrollments_query = Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).order_by(Enrollment.enrolled_at.desc())
    
    # Filter by progress if requested
    progress_filter = request.args.get('progress')
    enrollments = enrollments_query.all()
    
    student_data = []
    for enrollment in enrollments:
        if progress_filter == 'completed' and enrollment.progress_percent < 100:
            continue
        if progress_filter == 'in_progress' and (enrollment.progress_percent == 100 or enrollment.progress_percent == 0):
            continue
        if progress_filter == 'not_started' and enrollment.progress_percent > 0:
            continue
            
        is_completed = CourseCompletion.query.filter_by(student_id=enrollment.user_id, course_id=enrollment.course_id).first() is not None
        
        student_data.append({
            'enrollment': enrollment,
            'is_completed': is_completed
        })
    
    return render_template('dashboard/instructor_students.html', student_data=student_data, courses=courses)

@instructor_bp.route('/sessions', methods=['GET', 'POST'])
@login_required
@instructor_required
def sessions():
    """
    Route to manage live sessions.
    Accepts GET requests to list scheduled live sessions.
    Accepts POST requests to schedule a new live session and notify enrolled students.
    """
    from models import LiveSession
    from flask import request, flash, redirect, url_for
    from datetime import datetime
    
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        course_id = request.form.get('course_id')
        meeting_link = request.form.get('meeting_link')
        scheduled_date_str = request.form.get('scheduled_date')
        
        try:
            scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%dT%H:%M')
            new_session = LiveSession(
                title=title,
                course_id=course_id,
                instructor_id=current_user.id,
                meeting_link=meeting_link,
                scheduled_date=scheduled_date
            )
            db.session.add(new_session)
            db.session.commit()
            
            # Notify enrolled students
            from models import Enrollment
            from services.notification_service import send_notification
            enrollments = Enrollment.query.filter_by(course_id=course_id).all()
            for enrollment in enrollments:
                send_notification(
                    user_id=enrollment.user_id,
                    title="Live Session Scheduled",
                    message=f"A new live session '{title}' has been scheduled for '{new_session.course.title}'.",
                    notification_type='info',
                    icon='bi-camera-video',
                    action_url='/student/dashboard',
                    sender_id=current_user.id
                )
                
            flash('Live session scheduled successfully.', 'success')
            return redirect(url_for('instructor.sessions'))
        except ValueError:
            flash('Invalid date format.', 'error')
            
    live_sessions = LiveSession.query.filter_by(instructor_id=current_user.id).order_by(LiveSession.scheduled_date.asc()).all()
    
    return render_template('dashboard/instructor_sessions.html', courses=courses, live_sessions=live_sessions)

@instructor_bp.route('/course/<int:course_id>/assignments/new', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_assignment(course_id):
    """
    Route to create a new assignment for a course.
    Accepts form data to create an assignment and sends notifications to enrolled students.
    """
    from flask import request, flash, redirect, url_for
    from models import Assignment
    from datetime import datetime
    
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        total_marks = request.form.get('total_marks')
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M') if deadline_str else None
            new_assignment = Assignment(
                course_id=course.id,
                title=title,
                description=description,
                deadline=deadline,
                total_marks=int(total_marks) if total_marks else 0
            )
            db.session.add(new_assignment)
            
            # Send notification to enrolled students
            from models import Enrollment
            from services.notification_service import send_notification
            enrollments = Enrollment.query.filter_by(course_id=course.id).all()
            for enrollment in enrollments:
                send_notification(
                    user_id=enrollment.user_id,
                    title="New Assignment",
                    message=f"A new assignment '{title}' has been added to {course.title}.",
                    notification_type='primary',
                    icon='bi-journal-code',
                    action_url=f'/course/{course.id}/assignments',
                    sender_id=current_user.id
                )
                
            db.session.commit()
            flash('Assignment created successfully!', 'success')
            return redirect(url_for('assignment.list_assignments', course_id=course.id))
        except ValueError:
            flash('Invalid date or marks format.', 'error')
            
    return render_template('assignments/create_assignment.html', course=course)

@instructor_bp.route('/course/<int:course_id>/assignments/<int:assignment_id>/submissions', methods=['GET', 'POST'])
@login_required
@instructor_required
def grade_submissions(course_id, assignment_id):
    """
    Route to grade student submissions for an assignment.
    Displays submissions from students and allows the instructor to assign marks and provide feedback.
    Notifies the student once their submission is graded.
    """
    from flask import request, flash, redirect, url_for
    from models import Assignment, Submission
    
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    assignment = Assignment.query.filter_by(id=assignment_id, course_id=course.id).first_or_404()
    
    if request.method == 'POST':
        submission_id = request.form.get('submission_id')
        marks = request.form.get('marks')
        feedback = request.form.get('feedback')
        
        submission = Submission.query.get_or_404(submission_id)
        if submission.assignment_id == assignment.id:
            submission.marks_obtained = int(marks) if marks else 0
            submission.feedback = feedback
            submission.status = 'Graded'
            db.session.commit()
            
            from services.notification_service import send_notification
            send_notification(
                user_id=submission.student_id,
                title="Assignment Graded",
                message=f"Your submission for '{assignment.title}' has been graded.",
                notification_type='success',
                icon='bi-check-all',
                action_url=f'/course/{course.id}/assignments',
                sender_id=current_user.id
            )
            
            flash('Submission graded successfully.', 'success')
            
        return redirect(url_for('instructor.grade_submissions', course_id=course.id, assignment_id=assignment.id))
        
    all_submissions = Submission.query.filter_by(assignment_id=assignment.id).all()
    # Filter out any submissions accidentally made by non-students
    submissions = [s for s in all_submissions if s.student.role.name == 'student']
    
    return render_template('assignments/grade_submissions.html', course=course, assignment=assignment, submissions=submissions)

@instructor_bp.route('/course/<int:course_id>/quizzes/new', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_quiz(course_id):
    """
    Route to create a new quiz for a course.
    Parses JSON data containing quiz questions and answers, saves them, and notifies students.
    """
    from flask import request, flash, redirect, url_for
    from models import Quiz, Question, Answer, Lesson
    import json
    
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    lessons = Lesson.query.filter_by(course_id=course.id).order_by(Lesson.order_index).all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        timer_minutes = request.form.get('timer_minutes', 30)
        lesson_id_str = request.form.get('lesson_id')
        lesson_id = int(lesson_id_str) if lesson_id_str else None
        
        start_date_str = request.form.get('start_date')
        expiry_date_str = request.form.get('expiry_date')
        
        from datetime import datetime
        start_date = None
        expiry_date = None
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        if expiry_date_str:
            try:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass
        
        new_quiz = Quiz(
            course_id=course.id,
            lesson_id=lesson_id,
            title=title,
            timer_minutes=int(timer_minutes),
            start_date=start_date,
            expiry_date=expiry_date
        )
        db.session.add(new_quiz)
        db.session.flush() # Get the new_quiz.id
        
        quiz_data_str = request.form.get('quiz_data')
        if quiz_data_str:
            try:
                questions_list = json.loads(quiz_data_str)
                for q_data in questions_list:
                    new_q = Question(quiz_id=new_quiz.id, text=q_data['text'])
                    db.session.add(new_q)
                    db.session.flush()
                    
                    for a_data in q_data['answers']:
                        new_a = Answer(
                            question_id=new_q.id,
                            text=a_data['text'],
                            is_correct=a_data['is_correct']
                        )
                        db.session.add(new_a)
            except Exception as e:
                db.session.rollback()
                flash('Error parsing quiz data.', 'error')
                return redirect(url_for('instructor.create_quiz', course_id=course.id))
                
        # Send notification to enrolled students
        from models import Enrollment
        from services.notification_service import send_notification
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            send_notification(
                user_id=enrollment.user_id,
                title="New Quiz",
                message=f"A new quiz '{title}' has been added to {course.title}.",
                notification_type='primary',
                icon='bi-patch-question',
                action_url=f'/course/{course.id}/quizzes',
                sender_id=current_user.id
            )
            
        db.session.commit()
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('quiz.list_quizzes', course_id=course.id))
        
    return render_template('quizzes/create_quiz.html', course=course, lessons=lessons)

@instructor_bp.route('/course/<int:course_id>/quiz/<int:quiz_id>/results')
@login_required
@instructor_required
def quiz_results(course_id, quiz_id):
    """
    Route to view student results for a specific quiz.
    Retrieves and displays all quiz submissions ordered by their submission time.
    """
    from models import Quiz, Result
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    quiz = Quiz.query.filter_by(id=quiz_id, course_id=course.id).first_or_404()
    
    # Get all results for this quiz, ordered by submitted_at descending
    results = Result.query.filter_by(quiz_id=quiz.id).order_by(Result.submitted_at.desc()).all()
    
    return render_template('quizzes/quiz_results.html', course=course, quiz=quiz, results=results)

@instructor_bp.route('/subscription')
@login_required
@instructor_required
def subscription_management():
    from utils.helpers import get_instructor_usage
    from models import SubscriptionPlan
    usage = get_instructor_usage(current_user.id)
    plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    return render_template('dashboard/instructor_subscription.html', usage=usage, plans=plans)

@instructor_bp.route('/advanced-analytics')
@login_required
@instructor_required
def advanced_analytics():
    from utils.helpers import get_instructor_usage
    usage = get_instructor_usage(current_user.id)
    if not usage['has_advanced_analytics']:
        from flask import flash, redirect, url_for
        flash('Access denied. Your current plan does not support advanced analytics.', 'error')
        return redirect(url_for('instructor.subscription_management'))
    return render_template('dashboard/instructor_advanced_analytics.html')
