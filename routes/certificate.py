# Import Flask modules for routing, rendering templates, redirection, and user notifications
from flask import Blueprint, render_template, redirect, url_for, flash
# Import Flask-Login extensions to manage user sessions and authentication states
from flask_login import login_required, current_user
# Import custom decorator to restrict access to students only
from utils.decorators import student_required
# Import database models for querying and updating database records
from models import Certificate
from models import db

# Define the Blueprint for all certificate-related routes under the '/certificate' prefix
certificate_bp = Blueprint('certificate', __name__, url_prefix='/certificate')

@certificate_bp.route('/my-certificates')
@login_required
@student_required
def my_certificates():
    """
    Handles the my certificates functionality.
    Displays a list of all certificates earned by the currently logged-in student.
    """
    # Query all certificates belonging to the currently logged-in student
    certificates = Certificate.query.filter_by(student_id=current_user.id).all()
    # Render the certificate listing page with the retrieved records
    return render_template('certificates/my_certificates.html', certificates=certificates)

@certificate_bp.route('/view/<int:cert_id>')
def view_certificate(cert_id):
    """
    Handles the view certificate functionality.
    Renders the details of a specific certificate based on its ID.
    """
    # Fetch the specified certificate or return a 404 page if not found
    certificate = Certificate.query.get_or_404(cert_id)
    # Render the template to display the certificate details
    return render_template('certificates/view_certificate.html', certificate=certificate)

@certificate_bp.route('/retry-email/<int:cert_id>', methods=['POST'])
@login_required
def retry_email(cert_id):
    """
    Retries sending the certificate email.
    Allows a student to request another copy of their certificate via email if the previous attempt failed or was lost.
    """
    # Fetch the specified certificate or return a 404 page if not found
    certificate = Certificate.query.get_or_404(cert_id)
    
    # Check if the user is authorized: students should only be able to retry emails for their own certificates
    if current_user.role.name == 'student' and certificate.student_id != current_user.id:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('certificate.my_certificates'))
        
    # Local imports to prevent circular dependencies
    from services.email_service import send_certificate_email
    from datetime import datetime
    
    # Attempt to send the certificate PDF attachment to the student's email
    email_success = send_certificate_email(certificate.student, certificate.course, certificate.file_path)
    
    # If email delivery was successful, update the database flags and commit changes
    if email_success:
        certificate.email_sent = True
        certificate.email_sent_at = datetime.utcnow()
        db.session.commit()
        flash('Certificate email sent successfully!', 'success')
    else:
        # Keep original database state and notify the user of the failure
        flash('Failed to send certificate email. Please try again later.', 'error')
        
    # Redirect back to the student's certificate list
    return redirect(url_for('certificate.my_certificates'))