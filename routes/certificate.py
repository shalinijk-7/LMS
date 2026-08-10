# Handles certificate generation and management for completed courses.
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Certificate
from models import db

certificate_bp = Blueprint('certificate', __name__, url_prefix='/certificate')

@certificate_bp.route('/my-certificates')
@login_required
def my_certificates():
    certificates = Certificate.query.filter_by(student_id=current_user.id).all()
    return render_template('certificates/my_certificates.html', certificates=certificates)

@certificate_bp.route('/view/<int:cert_id>')
def view_certificate(cert_id):
    certificate = Certificate.query.get_or_404(cert_id)
    return render_template('certificates/view_certificate.html', certificate=certificate)
