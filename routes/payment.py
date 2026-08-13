# Handles course payments and payment history.
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Course, Enrollment, Payment
from utils.decorators import student_required
from datetime import datetime
import uuid

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')


@payment_bp.route('/checkout/<int:course_id>', methods=['GET', 'POST'])
@login_required
@student_required
def checkout(course_id):
    course = Course.query.get_or_404(course_id)

    # Already enrolled?
    already = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
    if already:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('courses.course_details', course_id=course.id))

    # Free course → direct enroll
    if not course.price or course.price <= 0:
        enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
        db.session.add(enrollment)
        db.session.commit()
        flash('Successfully enrolled in the free course!', 'success')
        return redirect(url_for('student.dashboard'))

    # Calculate tax (example: 18% GST)
    tax_rate = 0.18
    tax = round(course.price * tax_rate, 2)
    total = round(course.price + tax, 2)

    if request.method == 'POST':
        method = request.form.get('payment_method')

        if not method:
            flash('Please select a payment method.', 'danger')
            return redirect(url_for('payment.checkout', course_id=course.id))

        # Create payment record
        payment = Payment(
            student_id=current_user.id,
            course_id=course.id,
            amount=course.price,
            tax=tax,
            total_amount=total,
            payment_method=method,
            transaction_id=str(uuid.uuid4())[:12].upper(),
            status='Success',          # Simulated success (no real gateway yet)
            payment_date=datetime.utcnow()
        )
        db.session.add(payment)

        # Create enrollment
        enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
        db.session.add(enrollment)

        db.session.commit()

        return redirect(url_for('payment.success', payment_id=payment.id))

    return render_template(
        'payment/checkout.html',
        course=course,
        tax=tax,
        total=total
    )


@payment_bp.route('/history')
@login_required
@student_required
def history():
    payments = Payment.query.filter_by(student_id=current_user.id)\
                            .order_by(Payment.payment_date.desc()).all()
    return render_template('payment/history.html', payments=payments)
@payment_bp.route('/success/<int:payment_id>')
@login_required
@student_required
def success(payment_id):
    payment = Payment.query.filter_by(id=payment_id, student_id=current_user.id).first_or_404()
    return render_template('payment/success.html', payment=payment)