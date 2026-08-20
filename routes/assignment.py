# Handles assignment creation, submission, and evaluation.
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import Assignment, Submission, Course, db
import os
from werkzeug.utils import secure_filename
from datetime import datetime

assignment_bp = Blueprint('assignment', __name__, url_prefix='/assignment')

@assignment_bp.route('/course/<int:course_id>')
@login_required
def list_assignments(course_id):
    """
    Handles the list assignments functionality.
    """
    course = Course.query.get_or_404(course_id)
    assignments = Assignment.query.filter_by(course_id=course.id).all()
    # Check submissions for current user
    user_submissions = {sub.assignment_id: sub for sub in Submission.query.filter_by(student_id=current_user.id).all()}
    return render_template('assignments/assignment_list.html', course=course, assignments=assignments, user_submissions=user_submissions)

@assignment_bp.route('/view/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def view_assignment(assignment_id):
    """
    Handles the view assignment functionality.
    """
    assignment = Assignment.query.get_or_404(assignment_id)
    existing_submission = Submission.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
    
    if request.method == 'POST':
        if existing_submission:
            flash('You have already submitted this assignment.', 'warning')
            return redirect(url_for('assignment.view_assignment', assignment_id=assignment.id))
            
        if 'submission_file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
            
        file = request.files['submission_file']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file:
            filename = secure_filename(file.filename)
            # Create a unique filename to avoid overwriting
            unique_filename = f"user_{current_user.id}_assign_{assignment.id}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            new_submission = Submission(
                assignment_id=assignment.id,
                student_id=current_user.id,
                file_path=unique_filename
            )
            db.session.add(new_submission)
            db.session.commit()
            
            from services.notification_service import send_notification
            send_notification(
                user_id=assignment.course.instructor_id,
                title="New Assignment Submission",
                message=f"{current_user.name} submitted an assignment for '{assignment.title}'.",
                notification_type="info",
                icon="bi-file-earmark-check-fill",
                action_url="/instructor/dashboard"
            )
            flash('Assignment submitted successfully!', 'success')
            return redirect(url_for('assignment.view_assignment', assignment_id=assignment.id))
            
    return render_template('assignments/view_assignment.html', assignment=assignment, submission=existing_submission)
