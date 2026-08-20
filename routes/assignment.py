from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import Assignment, Submission, Course, db
import os
from werkzeug.utils import secure_filename
from datetime import datetime

# Initialize the Blueprint for assignment-related operations and routes
assignment_bp = Blueprint('assignment', __name__, url_prefix='/assignment')

@assignment_bp.route('/course/<int:course_id>')
@login_required
def list_assignments(course_id):
    """
    Handles the list assignments functionality.
    Retrieves and displays all assignments associated with a specific course,
    along with the submission status for the current logged-in user.
    """
    # Fetch the target course or return a 404 error if not found
    course = Course.query.get_or_404(course_id)
    
    # Retrieve all assignments associated with the specified course
    assignments = Assignment.query.filter_by(course_id=course.id).all()
    
    # Fetch and map the user's existing submissions to easily check completion status in the template
    user_submissions = {sub.assignment_id: sub for sub in Submission.query.filter_by(student_id=current_user.id).all()}
    
    return render_template('assignments/assignment_list.html', course=course, assignments=assignments, user_submissions=user_submissions)

@assignment_bp.route('/view/<int:assignment_id>', methods=['GET', 'POST'])
@login_required
def view_assignment(assignment_id):
    """
    Handles the view assignment functionality.
    - GET: Displays assignment details and submission status.
    - POST: Manages file upload validation, security, saving, database persistence, and notifying the instructor.
    """
    # Fetch the specified assignment or return a 404 error
    assignment = Assignment.query.get_or_404(assignment_id)
    
    if current_user.role.name == 'student':
        from services.subscription_service import check_feature_access
        has_access, message = check_feature_access(current_user.id, 'Assignments')
        if not has_access:
            return render_template('components/feature_locked.html', message=message)
    
    # Check if the current student has already submitted this assignment
    existing_submission = Submission.query.filter_by(assignment_id=assignment.id, student_id=current_user.id).first()
    
    if request.method == 'POST':
        # Prevent submission if one already exists
        if existing_submission:
            flash('You have already submitted this assignment.', 'warning')
            return redirect(url_for('assignment.view_assignment', assignment_id=assignment.id))
            
        # Ensure a file object is present in the request
        if 'submission_file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
            
        file = request.files['submission_file']
        
        # Ensure a file was actually selected for upload
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file:
            # Secure the filename against directory traversal attacks
            filename = secure_filename(file.filename)
            
            # Create a unique filename incorporating user and assignment context to avoid file collisions
            unique_filename = f"user_{current_user.id}_assign_{assignment.id}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Save the file to the configured uploads storage directory
            file.save(file_path)
            
            # Persist the submission record to the database
            new_submission = Submission(
                assignment_id=assignment.id,
                student_id=current_user.id,
                file_path=unique_filename
            )
            db.session.add(new_submission)
            db.session.commit()
            
            # Send real-time notification to the course instructor informing them of the submission
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