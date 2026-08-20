"""
Email Service Module

Provides functionality for sending transactional emails, such as course 
completion certificates, to users. Utilizes Flask-Mail for SMTP operations.
"""
import os
import logging
from flask import current_app
from flask_mail import Message
from app import mail

# Initialize logger for email-related activities
logger = logging.getLogger(__name__)

def send_certificate_email(student, course, file_path):
    """
    Sends an email with the certificate attached to the student.
    
    Args:
        student (User): The student who completed the course.
        course (Course): The course that was completed.
        file_path (str): The relative path to the certificate PDF (e.g. '/uploads/certificates/cert_ID.pdf')
        
    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    try:
        subject = f"Congratulations! You Completed {course.title}"
        
        # Find the specific certificate record for this course to get the issue date
        certificate_issued_at = "N/A"
        if student.certificates:
            for cert in student.certificates:
                if cert.course_id == course.id:
                    certificate_issued_at = cert.issued_at.strftime('%Y-%m-%d')
                    break
        
        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Certificate is Ready - AuraLearn</title>
</head>
<body style="margin: 0; padding: 0; background-color: #000000; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #000000; padding: 40px 20px;">
        <tr>
            <td align="center">
                <!-- Main Email Container -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #1A1A1A; border-radius: 8px; overflow: hidden; border: 1px solid #333333;">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0A0E27; padding: 35px 40px; border-bottom: 1px solid #1A1A1A;">
                            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                            <span style="color: #4A90E2;">Aura</span><span style="color: #F39C12;">Learn</span>
                                        </h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 12px;">
                                        <div style="color: #A0AEC0; font-size: 12px; letter-spacing: 1.5px; text-transform: uppercase;">
                                            <span style="color: #4A90E2; font-weight: bold; margin-right: 8px;">|</span> AURALEARN
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 40px; color: #E2E8F0; font-size: 15px; line-height: 1.6;">
                            <p style="margin: 0 0 20px 0;">Hi {student.name},</p>
                            
                            <p style="margin: 0 0 20px 0;">
                                Congratulations on successfully completing the course <strong>"{course.title}"</strong> instructed by {course.instructor.name if course.instructor else 'N/A'} on {certificate_issued_at}.
                            </p>
                            
                            <p style="margin: 0 0 20px 0;">
                                Your certificate of completion is ready. You can download and view it directly from your <a href="#" style="color: #4A90E2; text-decoration: none; font-weight: 500;">AuraLearn Certificates section</a>.
                            </p>
                            
                            <p style="margin: 0 0 25px 0;">Have a great day!</p>
                            
                            <p style="margin: 0 0 40px 0;">
                                Thanks,<br>
                                Your AuraLearn Team
                            </p>
                            
                            <p style="margin: 0; font-size: 12px; color: #718096;">
                                Too many notifications? Click <a href="#" style="color: #4A90E2; text-decoration: none;">here</a> to unsubscribe.
                            </p>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #0A0E27; padding: 25px 40px; border-top: 1px solid #1A1A1A;">
                            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="left" width="33%">
                                        <a href="#" style="color: #A0AEC0; text-decoration: none; font-size: 13px;">FAQ</a>
                                    </td>
                                    <td align="center" width="33%">
                                        <a href="#" style="color: #A0AEC0; text-decoration: none; font-size: 13px;">Manage Notifications</a>
                                    </td>
                                    <td align="right" width="33%">
                                        <a href="#" style="color: #A0AEC0; text-decoration: none; font-size: 13px;">Download App</a>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        body = f"""Hello {student.name},

Congratulations on successfully completing the
{course.title} course on AuraLearn!

Your certificate of completion is now available.

Course: {course.title}
Instructor: {course.instructor.name if course.instructor else 'N/A'}
Completion Date: {certificate_issued_at}

Your certificate is attached to this email.

You can also download and view your certificate
from your AuraLearn Certificates section.

Keep learning and achieving more!

Regards,
AuraLearn Team
"""
        msg = Message(subject=subject, recipients=[student.email])
        msg.body = body
        msg.html = html_body
        
        # Resolve absolute path for the PDF attachment based on the app's upload folder
        if file_path.startswith('/'):
            file_path = file_path[1:] # strip leading slash for correct os.path.join behavior
        
        # The file_path is something like 'uploads/certificates/cert_ID.pdf'
        base_dir = os.path.dirname(os.path.abspath(current_app.config['UPLOAD_FOLDER']))
        absolute_file_path = os.path.join(base_dir, file_path)
        
        attachment_filename = f"AuraLearn_Certificate_{student.name.replace(' ', '_')}_{course.title.replace(' ', '_')}.pdf"
        
        if os.path.exists(absolute_file_path):
            with open(absolute_file_path, 'rb') as f:
                msg.attach(attachment_filename, 'application/pdf', f.read())
        else:
            logger.error(f"Certificate file not found for attachment: {absolute_file_path}")
            return False
            
        mail.send(msg)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send certificate email to {student.email} for course {course.title}: {str(e)}")
        return False




def send_subscription_success_email(student, plan, payment, subscription):

    """

    Sends a subscription success email to the student.

    

    Args:

        student (User): The student who subscribed.

        plan (SubscriptionPlan): The plan subscribed to.

        payment (Payment): The payment record.

        subscription (Subscription): The subscription record.

        

    Returns:

        bool: True if email sent successfully, False otherwise.

    """

    try:

        subject = f"Your {plan.name} Subscription is Now Active ��   AuraLearn"

        

        start_date_str = subscription.start_date.strftime('%d %B %Y') if subscription.start_date else 'N/A'

        expiry_date_str = subscription.end_date.strftime('%d %B %Y') if subscription.end_date else 'N/A'

        payment_date_str = payment.payment_date.strftime('%d %B %Y') if payment.payment_date else 'N/A'

        

        # Calculate pricing details

        original_amount = payment.amount + payment.discount_amount

        discount_amount = payment.discount_amount

        # Recalculate tax and base price based on total paid to display properly if needed

        # Or use the stored amount. The prompt says: "Total Paid: � �[Final Amount]"

        # Assuming original amount before tax & discount. In the checkout logic:

        # discounted_price = plan.price - discount_amount

        # tax = discounted_price * 0.05

        # total_amount = discounted_price + tax

        

        discounted_price = payment.amount / 1.05

        tax = payment.amount - discounted_price

        original_price = discounted_price + payment.discount_amount

        

        currency_symbol = '� �' if payment.currency == 'INR' else ('� �' if payment.currency == 'EUR' else '$')

        

        html_body = f"""<!DOCTYPE html>

<html lang="en">

<head>

    <meta charset="UTF-8">

    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Subscription Activated Successfully ��   AuraLearn</title>

</head>

<body style="margin: 0; padding: 0; background-color: #000000; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">

    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #000000; padding: 40px 20px;">

        <tr>

            <td align="center">

                <!-- Main Email Container -->

                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #1A1A1A; border-radius: 8px; overflow: hidden; border: 1px solid #333333; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">

                    

                    <!-- Header -->

                    <tr>

                        <td style="background-color: #4A90E2; padding: 30px 40px; text-align: center;">

                            <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">

                                AuraLearn

                            </h1>

                        </td>

                    </tr>



                    <!-- Body Content -->

                    <tr>

                        <td style="padding: 40px; color: #E2E8F0; font-size: 16px; line-height: 1.6;">

                            <p style="margin: 0 0 20px 0;">Hi {student.name},</p>

                            

                            <p style="margin: 0 0 20px 0;">

                                Congratulations! Your AuraLearn subscription has been successfully activated.

                            </p>

                            

                            <p style="margin: 0 0 30px 0;">

                                Your subscription is now active and you can access the features and courses included in your selected plan.

                            </p>

                            

                            <!-- Subscription Details Card -->

                            <div style="background-color: #2D3748; border: 1px solid #4A5568; border-radius: 6px; padding: 20px; margin-bottom: 25px;">

                                <h3 style="margin: 0 0 15px 0; font-size: 14px; text-transform: uppercase; color: #A0AEC0; letter-spacing: 1px;">Subscription Details</h3>

                                

                                <table width="100%" border="0" cellpadding="4" cellspacing="0" style="font-size: 14px;">

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;" width="45%">Plan:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{plan.name}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Amount Paid:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{payment.amount:.2f}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Subscription Duration:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{plan.duration_days} Days</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Start Date:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{start_date_str}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Expiry Date:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{expiry_date_str}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0;">Subscription Status:</td>

                                        <td style="font-weight: 600; color: #10b981;">{subscription.status.upper()}</td>

                                    </tr>

                                </table>

                            </div>

                            

                            <!-- Payment Details Card -->

                            <div style="background-color: #2D3748; border: 1px solid #4A5568; border-radius: 6px; padding: 20px; margin-bottom: 30px;">

                                <h3 style="margin: 0 0 15px 0; font-size: 14px; text-transform: uppercase; color: #A0AEC0; letter-spacing: 1px;">Payment Details</h3>

                                

                                <table width="100%" border="0" cellpadding="4" cellspacing="0" style="font-size: 14px;">

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;" width="45%">Payment Status:</td>

                                        <td style="font-weight: 600; color: #10b981; padding-bottom: 8px;">Successful</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Transaction ID:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{payment.transaction_id}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Invoice Number:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">INV-{payment.transaction_id}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Payment Date:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{payment_date_str}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Original Amount:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{original_price:.2f}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Discount:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{discount_amount:.2f}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Tax:</td>

                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{tax:.2f}</td>

                                    </tr>

                                    <tr>

                                        <td style="color: #A0AEC0; padding-top: 8px; border-top: 1px solid #e2e8f0;">Total Paid:</td>

                                        <td style="font-weight: 700; font-size: 16px; padding-top: 8px; border-top: 1px solid #e2e8f0;">{currency_symbol}{payment.amount:.2f}</td>

                                    </tr>

                                </table>

                            </div>

                            

                            <!-- Call to Action Buttons -->

                            <div style="text-align: center; margin-bottom: 20px;">

                                <a href="https://auralearn.example.com/student/dashboard" style="display: inline-block; background-color: #4A90E2; color: #ffffff; text-decoration: none; font-weight: 600; padding: 12px 24px; border-radius: 4px; margin-bottom: 10px;">Go to My Dashboard</a>

                            </div>

                            

                            <div style="text-align: center; margin-bottom: 10px;">

                                <a href="https://auralearn.example.com/student/payment-history" style="display: inline-block; color: #4A90E2; text-decoration: underline; font-weight: 500; margin: 0 10px;">View Payment History</a>

                                <span style="color: #4A5568;">|</span>

                                <a href="https://auralearn.example.com/payment/invoice/{payment.transaction_id}" style="display: inline-block; color: #4A90E2; text-decoration: underline; font-weight: 500; margin: 0 10px;">Download Invoice</a>

                            </div>

                        </td>

                    </tr>



                    <!-- Footer -->

                    <tr>

                        <td style="background-color: #2D3748; padding: 30px 40px; border-top: 1px solid #e2e8f0; text-align: center;">

                            <p style="margin: 0 0 10px 0; color: #A0AEC0; font-size: 14px;">Thank you for choosing AuraLearn.</p>

                            <p style="margin: 0 0 20px 0; color: #A0AEC0; font-size: 14px; font-weight: 600;">Keep learning. Keep growing.</p>

                            <p style="margin: 0 0 25px 0; color: #A0AEC0; font-size: 14px;">Regards,<br>AuraLearn Team</p>

                            

                            <p style="margin: 0; color: #718096; font-size: 12px;">&copy; 2026 AuraLearn. All rights reserved.</p>

                        </td>

                    </tr>

                    

                </table>

            </td>

        </tr>

    </table>

</body>

</html>"""



        body = f"""Hi {student.name},



Congratulations! Your AuraLearn subscription has been successfully activated.



Your subscription is now active and you can enjoy the features included in your selected plan.



SUBSCRIPTION DETAILS

Plan: {plan.name}

Amount Paid: {currency_symbol}{payment.amount:.2f}

Duration: {plan.duration_days} Days

Start Date: {start_date_str}

Expiry Date: {expiry_date_str}

Status: {subscription.status.upper()}



PAYMENT DETAILS

Payment Status: Successful

Transaction ID: {payment.transaction_id}

Invoice Number: INV-{payment.transaction_id}

Payment Date: {payment_date_str}

Original Amount: {currency_symbol}{original_price:.2f}

Discount: {currency_symbol}{discount_amount:.2f}

Tax: {currency_symbol}{tax:.2f}

Total Paid: {currency_symbol}{payment.amount:.2f}





Thank you for choosing AuraLearn.

Keep learning. Keep growing.



Regards,

AuraLearn Team

�� 2026 AuraLearn. All rights reserved.

"""

        msg = Message(subject=subject, recipients=[student.email])

        msg.body = body

        msg.html = html_body

        

        mail.send(msg)

        return True

        

    except Exception as e:

        logger.error(f"Failed to send subscription success email to {student.email}: {str(e)}")

        # Do NOT raise the exception, just return False so that the payment flow doesn't rollback

        return False




def send_subscription_success_email(student, plan, payment, subscription):
    """
    Sends a subscription success email to the student.
    
    Args:
        student (User): The student who subscribed.
        plan (SubscriptionPlan): The plan subscribed to.
        payment (Payment): The payment record.
        subscription (Subscription): The subscription record.
        
    Returns:
        bool: True if email sent successfully, False otherwise.
    """
    try:
        subject = f"Your {plan.name} Subscription is Now Active – AuraLearn"
        
        start_date_str = subscription.start_date.strftime('%d %B %Y') if subscription.start_date else 'N/A'
        expiry_date_str = subscription.end_date.strftime('%d %B %Y') if subscription.end_date else 'N/A'
        payment_date_str = payment.payment_date.strftime('%d %B %Y') if payment.payment_date else 'N/A'
        
        # Calculate pricing details
        original_amount = payment.amount + payment.discount_amount
        discount_amount = payment.discount_amount
        # Recalculate tax and base price based on total paid to display properly if needed
        # Or use the stored amount. The prompt says: "Total Paid: ₹[Final Amount]"
        # Assuming original amount before tax & discount. In the checkout logic:
        # discounted_price = plan.price - discount_amount
        # tax = discounted_price * 0.05
        # total_amount = discounted_price + tax
        
        discounted_price = payment.amount / 1.05
        tax = payment.amount - discounted_price

        from flask import url_for
        dashboard_url = url_for('student.dashboard', _external=True)
        history_url = url_for('student.payment_history', _external=True)
        invoice_url = url_for('payment.invoice', transaction_id=payment.transaction_id, _external=True)

        original_price = discounted_price + payment.discount_amount
        
        currency_symbol = '₹' if payment.currency == 'INR' else ('€' if payment.currency == 'EUR' else '$')
        
        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Subscription Activated Successfully – AuraLearn</title>
</head>
<body style="margin: 0; padding: 0; background-color: #000000; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
    <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color: #000000; padding: 40px 20px;">
        <tr>
            <td align="center">
                <!-- Main Email Container -->
                <table width="100%" border="0" cellpadding="0" cellspacing="0" style="max-width: 600px; background-color: #1A1A1A; border-radius: 8px; overflow: hidden; border: 1px solid #333333; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background-color: #0A0E27; padding: 35px 40px; border-bottom: 1px solid #1A1A1A;">
                            <table width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td>
                                        <h1 style="margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">
                                            <span style="color: #4A90E2;">Aura</span><span style="color: #F39C12;">Learn</span>
                                        </h1>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding-top: 12px;">
                                        <div style="color: #A0AEC0; font-size: 12px; letter-spacing: 1.5px; text-transform: uppercase;">
                                            <span style="color: #4A90E2; font-weight: bold; margin-right: 8px;">|</span> AURALEARN
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 40px; color: #E2E8F0; font-size: 16px; line-height: 1.6;">
                            <p style="margin: 0 0 20px 0;">Hi {student.name},</p>
                            
                            <p style="margin: 0 0 20px 0;">
                                Congratulations! Your AuraLearn subscription has been successfully activated.
                            </p>
                            
                            <p style="margin: 0 0 30px 0;">
                                Your subscription is now active and you can access the features and courses included in your selected plan.
                            </p>
                            
                            <!-- Subscription Details Card -->
                            <div style="background-color: #2D3748; border: 1px solid #4A5568; border-radius: 6px; padding: 20px; margin-bottom: 25px;">
                                <h3 style="margin: 0 0 15px 0; font-size: 14px; text-transform: uppercase; color: #A0AEC0; letter-spacing: 1px;">Subscription Details</h3>
                                
                                <table width="100%" border="0" cellpadding="4" cellspacing="0" style="font-size: 14px;">
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;" width="45%">Plan:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{plan.name}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Amount Paid:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{payment.amount:.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Subscription Duration:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{plan.duration_days} Days</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Start Date:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{start_date_str}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Expiry Date:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{expiry_date_str}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0;">Subscription Status:</td>
                                        <td style="font-weight: 600; color: #10b981;">{subscription.status.upper()}</td>
                                    </tr>
                                </table>
                            </div>
                            
                            <!-- Payment Details Card -->
                            <div style="background-color: #2D3748; border: 1px solid #4A5568; border-radius: 6px; padding: 20px; margin-bottom: 30px;">
                                <h3 style="margin: 0 0 15px 0; font-size: 14px; text-transform: uppercase; color: #A0AEC0; letter-spacing: 1px;">Payment Details</h3>
                                
                                <table width="100%" border="0" cellpadding="4" cellspacing="0" style="font-size: 14px;">
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;" width="45%">Payment Status:</td>
                                        <td style="font-weight: 600; color: #10b981; padding-bottom: 8px;">Successful</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Transaction ID:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{payment.transaction_id}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Invoice Number:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">INV-{payment.transaction_id}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Payment Date:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{payment_date_str}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Original Amount:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{original_price:.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Discount:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{discount_amount:.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-bottom: 8px;">Tax:</td>
                                        <td style="font-weight: 600; padding-bottom: 8px;">{currency_symbol}{tax:.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="color: #A0AEC0; padding-top: 8px; border-top: 1px solid #e2e8f0;">Total Paid:</td>
                                        <td style="font-weight: 700; font-size: 16px; padding-top: 8px; border-top: 1px solid #e2e8f0;">{currency_symbol}{payment.amount:.2f}</td>
                                    </tr>
                                </table>
                            </div>
                            
                            <!-- Call to Action Buttons -->
                            <div style="text-align: center; margin-bottom: 20px;">
                                <a href="{dashboard_url}" style="display: inline-block; background-color: #4A90E2; color: #ffffff; text-decoration: none; font-weight: 600; padding: 12px 24px; border-radius: 4px; margin-bottom: 10px;">Go to My Dashboard</a>
                            </div>
                            
                            <div style="text-align: center; margin-bottom: 10px;">
                                <a href="{history_url}" style="display: inline-block; color: #4A90E2; text-decoration: underline; font-weight: 500; margin: 0 10px;">View Payment History</a>
                                <span style="color: #4A5568;">|</span>
                                <a href="{invoice_url}" style="display: inline-block; color: #4A90E2; text-decoration: underline; font-weight: 500; margin: 0 10px;">Download Invoice</a>
                            </div>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #2D3748; padding: 30px 40px; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0 0 10px 0; color: #A0AEC0; font-size: 14px;">Thank you for choosing AuraLearn.</p>
                            <p style="margin: 0 0 20px 0; color: #A0AEC0; font-size: 14px; font-weight: 600;">Keep learning. Keep growing.</p>
                            <p style="margin: 0 0 25px 0; color: #A0AEC0; font-size: 14px;">Regards,<br>AuraLearn Team</p>
                            
                            <p style="margin: 0; color: #718096; font-size: 12px;">&copy; 2026 AuraLearn. All rights reserved.</p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

        body = f"""Hi {student.name},

Congratulations! Your AuraLearn subscription has been successfully activated.

Your subscription is now active and you can enjoy the features included in your selected plan.

SUBSCRIPTION DETAILS
Plan: {plan.name}
Amount Paid: {currency_symbol}{payment.amount:.2f}
Duration: {plan.duration_days} Days
Start Date: {start_date_str}
Expiry Date: {expiry_date_str}
Status: {subscription.status.upper()}

PAYMENT DETAILS
Payment Status: Successful
Transaction ID: {payment.transaction_id}
Invoice Number: INV-{payment.transaction_id}
Payment Date: {payment_date_str}
Original Amount: {currency_symbol}{original_price:.2f}
Discount: {currency_symbol}{discount_amount:.2f}
Tax: {currency_symbol}{tax:.2f}
Total Paid: {currency_symbol}{payment.amount:.2f}


Thank you for choosing AuraLearn.
Keep learning. Keep growing.

Regards,
AuraLearn Team
© 2026 AuraLearn. All rights reserved.
"""
        from utils.email import send_email
        return send_email(subject, student.email, body, html_body)
        
    except Exception as e:
        logger.error(f"Failed to send subscription success email to {student.email}: {str(e)}")
        # Do NOT raise the exception, just return False so that the payment flow doesn't rollback
        return False
