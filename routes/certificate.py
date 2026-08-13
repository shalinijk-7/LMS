from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import Certificate
from models import db

certificate_bp = Blueprint('certificate', __name__, url_prefix='/certificate')

@certificate_bp.route('/my-certificates')
@login_required
@student_required
def my_certificates():
    """
    Handles the my certificates functionality.
    """
    certificates = Certificate.query.filter_by(student_id=current_user.id).all()
    return render_template('certificates/my_certificates.html', certificates=certificates)

@certificate_bp.route('/view/<int:cert_id>')
def view_certificate(cert_id):
    """
    Handles the view certificate functionality.
    """
    certificate = Certificate.query.get_or_404(cert_id)
    return render_template('certificates/view_certificate.html', certificate=certificate)

@certificate_bp.route('/retry-email/<int:cert_id>', methods=['POST'])
@login_required
def retry_email(cert_id):
    """
    Retries sending the certificate email.
    """
    certificate = Certificate.query.get_or_404(cert_id)
    
    # Check if the user is authorized
    if current_user.role.name == 'student' and certificate.student_id != current_user.id:
        flash('You are not authorized to perform this action.', 'error')
        return redirect(url_for('certificate.my_certificates'))
        
    from services.email_service import send_certificate_email
    from datetime import datetime
    
    email_success = send_certificate_email(certificate.student, certificate.course, certificate.file_path)
    
    if email_success:
        certificate.email_sent = True
        certificate.email_sent_at = datetime.utcnow()
        db.session.commit()
        flash('Certificate email sent successfully!', 'success')
    else:
        flash('Failed to send certificate email. Please try again later.', 'error')
        
    return redirect(url_for('certificate.my_certificates'))
