from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Course, Payment, PurchaseHistory, Enrollment
from datetime import datetime
import uuid

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')

@payment_bp.route('/checkout/<int:course_id>')
@login_required
def checkout(course_id):
    """
    Handles the checkout functionality.
    """
    if current_user.role.name != 'student':
        flash('Only students can purchase courses.', 'error')
        return redirect(url_for('courses.course_details', course_id=course_id))
        
    course = Course.query.get_or_404(course_id)
    
    if course.course_type == 'Free':
        flash('This course is free. You can enroll directly.', 'info')
        return redirect(url_for('courses.course_details', course_id=course.id))
        
    # Check if already enrolled
    existing = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.dashboard'))
        
    tax = round(course.price * 0.05, 2) # 5% tax example
    total_amount = round(course.price + tax, 2)
        
    return render_template('payment/checkout.html', course=course, tax=tax, total_amount=total_amount)

@payment_bp.route('/process/<int:course_id>', methods=['POST'])
@login_required
def process_payment(course_id):
    """
    Handles the process payment functionality.
    """
    if current_user.role.name != 'student':
        return redirect(url_for('main.index'))
        
    course = Course.query.get_or_404(course_id)
    payment_method = request.form.get('payment_method', 'Card')
    
    # Simulate a successful payment processing
    transaction_id = str(uuid.uuid4()).upper().replace('-', '')[:16]
    
    tax = round(course.price * 0.05, 2)
    total_amount = round(course.price + tax, 2)
    
    # 1. Create Payment record
    new_payment = Payment(
        student_id=current_user.id,
        course_id=course.id,
        amount=total_amount,
        currency=course.currency,
        payment_method=payment_method,
        transaction_id=transaction_id,
        status='Success'
    )
    db.session.add(new_payment)
    db.session.flush() # to get new_payment.id
    
    # 2. Create Purchase History
    new_purchase = PurchaseHistory(
        student_id=current_user.id,
        course_id=course.id,
        payment_id=new_payment.id
    )
    db.session.add(new_purchase)
    
    # 3. Enroll Student
    new_enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
    db.session.add(new_enrollment)
    
    # 4. Notify Instructor
    from services.notification_service import send_notification
    send_notification(
        user_id=course.instructor_id,
        title="New Course Sale",
        message=f"{current_user.name} just purchased '{course.title}'.",
        notification_type="success",
        icon="bi-currency-exchange",
        action_url="/instructor/dashboard"
    )
    
    db.session.commit()
    
    flash('Payment successful! You are now enrolled.', 'success')
    return redirect(url_for('payment.success', transaction_id=transaction_id))

@payment_bp.route('/success/<transaction_id>')
@login_required
def success(transaction_id):
    """
    Handles the success functionality.
    """
    payment = Payment.query.filter_by(transaction_id=transaction_id).first_or_404()
    
    # Ensure current user is the owner
    if payment.student_id != current_user.id:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('student.dashboard'))
        
    return render_template('payment/success.html', payment=payment)
