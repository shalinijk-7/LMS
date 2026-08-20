# Handles course payments and payment history.
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import db, Course, Payment, PurchaseHistory, Enrollment
from datetime import datetime
import uuid
from services.notification_service import send_notification

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')


@payment_bp.route('/checkout/<int:course_id>', methods=['GET', 'POST'])
@login_required
@student_required
def checkout(course_id):
    """Show checkout page or process a simulated payment."""
    course = Course.query.get_or_404(course_id)

    # Already enrolled?
    existing = Enrollment.query.filter_by(
        user_id=current_user.id, course_id=course.id
    ).first()
    if existing:
        flash('You are already enrolled in this course.', 'info')
        return redirect(url_for('student.dashboard'))

    # Free course → direct enroll
    if getattr(course, 'course_type', None) == 'Free' or not course.price or course.price <= 0:
        enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
        db.session.add(enrollment)
        db.session.commit()

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

        flash('Successfully enrolled in the free course!', 'success')
        return redirect(url_for('student.dashboard'))

    # Calculate tax (example: 5%)
    tax_rate = 0.05
    tax = round(course.price * tax_rate, 2)
    total_amount = round(course.price + tax, 2)

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        if not payment_method:
            flash('Please select a payment method.', 'danger')
            return redirect(url_for('payment.checkout', course_id=course.id))

        transaction_id = str(uuid.uuid4()).upper().replace('-', '')[:16]

        # 1. Create Payment record
        new_payment = Payment(
            student_id=current_user.id,
            course_id=course.id,
            amount=course.price,
            currency=getattr(course, 'currency', 'USD'),
            tax=tax,
            total_amount=total_amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status='Success',
            payment_date=datetime.utcnow()
        )
        db.session.add(new_payment)
        db.session.flush()  # get new_payment.id

        # 2. Create Purchase History (if model exists)
        try:
            new_purchase = PurchaseHistory(
                student_id=current_user.id,
                course_id=course.id,
                payment_id=new_payment.id
            )
            db.session.add(new_purchase)
        except Exception:
            pass  # PurchaseHistory may not be used in every setup

        # 3. Enroll Student
        new_enrollment = Enrollment(user_id=current_user.id, course_id=course.id)
        db.session.add(new_enrollment)

        # 4. Notifications
        send_notification(
            user_id=course.instructor_id,
            title="New Course Sale",
            message=f"{current_user.name} just purchased '{course.title}'.",
            notification_type="success",
            icon="bi-currency-exchange",
            action_url="/instructor/dashboard"
        )
        send_notification(
            user_id=current_user.id,
            title="Payment Successful",
            message=f"You have successfully purchased and enrolled in '{course.title}'.",
            notification_type="success",
            icon="bi-bag-check-fill",
            action_url=f"/courses/{course.id}/start"
        )

        db.session.commit()

        flash('Payment successful! You are now enrolled.', 'success')
        return redirect(url_for('payment.success', payment_id=new_payment.id))

    return render_template(
        'payment/checkout.html',
        course=course,
        tax=tax,
        total_amount=total_amount
    )


@payment_bp.route('/success/<int:payment_id>')
@login_required
@student_required
def success(payment_id):
    """Show payment success page."""
    payment = Payment.query.filter_by(
        id=payment_id, student_id=current_user.id
    ).first_or_404()
    return render_template('payment/success.html', payment=payment)


@payment_bp.route('/history')
@login_required
@student_required
def history():
    """Show payment history for the current student."""
    payments = Payment.query.filter_by(
        student_id=current_user.id
    ).order_by(Payment.payment_date.desc()).all()
    return render_template('payment/history.html', payments=payments)