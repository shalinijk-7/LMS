from flask import Blueprint, render_template
from flask_login import login_required, current_user
from utils.decorators import instructor_required
from models import db, Course

instructor_bp = Blueprint('instructor', __name__, url_prefix='/instructor')

@instructor_bp.route('/dashboard')
@login_required
@instructor_required
def dashboard():
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    
    total_students = sum(len(course.enrollments) for course in courses)
    total_revenue = sum(course.price * len(course.enrollments) for course in courses if course.price)
    
    return render_template('dashboard/instructor_dashboard.html', 
                           courses=courses, 
                           total_students=total_students, 
                           total_revenue=total_revenue)

@instructor_bp.route('/students')
@login_required
@instructor_required
def students():
    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    # Sort courses so that courses with enrollments appear first
    courses.sort(key=lambda c: len(c.enrollments), reverse=True)
    course_ids = [c.id for c in courses]
    
    from models import Enrollment, User
    # Get all enrollments for the instructor's courses
    enrollments = Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).order_by(Enrollment.enrolled_at.desc()).all()
    
    return render_template('dashboard/instructor_students.html', enrollments=enrollments, courses=courses)

@instructor_bp.route('/sessions', methods=['GET', 'POST'])
@login_required
@instructor_required
def sessions():
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
            flash('Live session scheduled successfully!', 'success')
            return redirect(url_for('instructor.sessions'))
        except ValueError:
            flash('Invalid date format.', 'error')
            
    live_sessions = LiveSession.query.filter_by(instructor_id=current_user.id).order_by(LiveSession.scheduled_date.asc()).all()
    
    return render_template('dashboard/instructor_sessions.html', courses=courses, live_sessions=live_sessions)

@instructor_bp.route('/course/<int:course_id>/assignments/new', methods=['GET', 'POST'])
@login_required
@instructor_required
def create_assignment(course_id):
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
            from models import Enrollment, Notification
            enrollments = Enrollment.query.filter_by(course_id=course.id).all()
            for enrollment in enrollments:
                notif = Notification(
                    user_id=enrollment.user_id,
                    title="New Assignment",
                    message=f"A new assignment '{title}' has been added to {course.title}."
                )
                db.session.add(notif)
                
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
        from models import Enrollment, Notification
        enrollments = Enrollment.query.filter_by(course_id=course.id).all()
        for enrollment in enrollments:
            notif = Notification(
                user_id=enrollment.user_id,
                title="New Quiz",
                message=f"A new quiz '{title}' has been added to {course.title}."
            )
            db.session.add(notif)
            
        db.session.commit()
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('quiz.list_quizzes', course_id=course.id))
        
    return render_template('quizzes/create_quiz.html', course=course, lessons=lessons)

@instructor_bp.route('/course/<int:course_id>/quiz/<int:quiz_id>/results')
@login_required
@instructor_required
def quiz_results(course_id, quiz_id):
    from models import Quiz, Result
    course = Course.query.filter_by(id=course_id, instructor_id=current_user.id).first_or_404()
    quiz = Quiz.query.filter_by(id=quiz_id, course_id=course.id).first_or_404()
    
    # Get all results for this quiz, ordered by submitted_at descending
    results = Result.query.filter_by(quiz_id=quiz.id).order_by(Result.submitted_at.desc()).all()
    
    return render_template('quizzes/quiz_results.html', course=course, quiz=quiz, results=results)
