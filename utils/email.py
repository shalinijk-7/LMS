# Contains helper functions for sending emails.
import secrets
import string
import os
from flask import current_app
from flask_mail import Message


def send_email(subject, recipient, body, html_body=None, attachments=None):
    """
    Send an email.
    attachments is a list of tuples: (filename, path_or_bytes, mimetype)
    """
    mail = current_app.extensions.get('mail')
    if not mail:
        print("Mail extension not found. Logging email instead:")
        print(f"Subject: {subject}\nTo: {recipient}\nBody: {body}")
        return False

    try:
        # Send a BCC to the developer's email so they can view OTPs for fake test accounts
        dev_email = 'madaka951@gmail.com'
        msg = Message(subject, recipients=[recipient], bcc=[dev_email])
        msg.body = body
        if html_body:
            msg.html = html_body

        if attachments:
            for filename, data_or_path, mimetype in attachments:
                if isinstance(data_or_path, (bytes, bytearray)):
                    msg.attach(filename, mimetype, data_or_path)
                else:
                    # treat as file path
                    with open(data_or_path, 'rb') as f:
                        msg.attach(filename, mimetype, f.read())

        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        print(f"Fallback Logging - Subject: {subject}\nTo: {recipient}\nBody: {body}")
        return False


def generate_otp(length=6):
    """Generate a secure 6-digit OTP."""
    digits = string.digits
    return ''.join(secrets.choice(digits) for i in range(length))


def send_otp_email(recipient, otp):
    """Send OTP email for password reset."""
    subject = "Your Password Reset OTP - AuraLearn"
    body = f"Hello,\n\nYour OTP for password reset is: {otp}\n\nThis OTP will expire in 10 minutes.\nIf you did not request this, please ignore this email.\n\nAuraLearn Team"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
        <h2 style="color: #7c3aed;">Password Reset Request</h2>
        <p>Hello,</p>
        <p>We received a request to reset your password. Use the following One-Time Password (OTP) to proceed:</p>
        <div style="background-color: #f3f4f6; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <h1 style="letter-spacing: 5px; color: #1f2937; margin: 0;">{otp}</h1>
        </div>
        <p style="color: #ef4444; font-size: 0.9em;">This OTP will expire in 10 minutes.</p>
        <p>If you did not request a password reset, please ignore this email or contact support.</p>
        <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 0.8em; text-align: center;">AuraLearn Team</p>
    </div>
    """
    return send_email(subject, recipient, body, html_body)


def send_2fa_otp_email(recipient, otp):
    """Send 2FA OTP email to the user."""
    subject = "Your 2FA Login Code - AuraLearn"
    body = f"Hello,\n\nYour Two-Factor Authentication code is: {otp}\n\nThis code will expire in 5 minutes.\nIf you did not attempt to log in, please secure your account immediately.\n\nAuraLearn Team"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
        <h2 style="color: #2563EB;">Two-Factor Authentication</h2>
        <p>Hello,</p>
        <p>Use the following One-Time Password (OTP) to complete your login:</p>
        <div style="background-color: #f3f4f6; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <h1 style="letter-spacing: 5px; color: #1f2937; margin: 0;">{otp}</h1>
        </div>
        <p style="color: #ef4444; font-size: 0.9em;">This OTP will expire in 5 minutes.</p>
        <p>If you did not attempt to log in, please secure your account immediately.</p>
        <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 0.8em; text-align: center;">AuraLearn Team</p>
    </div>
    """
    return send_email(subject, recipient, body, html_body)


def send_certificate_email(recipient, student_name, course_title, certificate_id,
                           instructor_name=None, completion_date=None,
                           download_url=None, pdf_path=None):
    """
    Send a professional certificate email with optional PDF attachment.
    """
    subject = f"🎉 Congratulations! Your Certificate for “{course_title}” is Ready – AuraLearn"

    body = f"""Hello {student_name},

Congratulations on successfully completing the course "{course_title}"!

Your official certificate has been generated.
Certificate ID: {certificate_id}

You can view and download your certificate from your dashboard.

Keep learning and growing!
AuraLearn Team
"""

    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%); padding: 32px 24px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 700;">AuraLearn</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 15px;">Certificate of Completion</p>
        </div>

        <!-- Body -->
        <div style="padding: 36px 28px;">
            <h2 style="color: #111827; margin: 0 0 12px 0; font-size: 24px;">
                Congratulations, {student_name}! 🎉
            </h2>
            
            <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin-bottom: 24px;">
                You have successfully completed the course<br>
                <strong style="color: #7c3aed; font-size: 18px;">{course_title}</strong>
            </p>

            <!-- Certificate Details Card -->
            <div style="background: #f5f3ff; border: 1px solid #ede9fe; border-radius: 12px; padding: 24px; margin-bottom: 28px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #6b7280; font-size: 14px;">Certificate ID</td>
                        <td style="padding: 6px 0; text-align: right; font-weight: 700; color: #5b21b6; font-size: 15px; letter-spacing: 0.5px;">{certificate_id}</td>
                    </tr>
                    {"<tr><td style='padding: 6px 0; color: #6b7280; font-size: 14px;'>Instructor</td><td style='padding: 6px 0; text-align: right; font-weight: 600; color: #111827;'>" + instructor_name + "</td></tr>" if instructor_name else ""}
                    {"<tr><td style='padding: 6px 0; color: #6b7280; font-size: 14px;'>Completion Date</td><td style='padding: 6px 0; text-align: right; font-weight: 600; color: #111827;'>" + completion_date + "</td></tr>" if completion_date else ""}
                </table>
            </div>

            <p style="color: #4b5563; font-size: 15px; line-height: 1.6;">
                Your official certificate PDF is attached to this email.  
                You can also download it anytime from your student dashboard.
            </p>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 32px 0 12px 0;">
                <a href="{download_url or '#'}" 
                   style="background: linear-gradient(135deg, #7c3aed, #a855f7); 
                          color: white; 
                          padding: 14px 32px; 
                          text-decoration: none; 
                          border-radius: 50px; 
                          font-weight: 600; 
                          font-size: 15px;
                          display: inline-block;
                          box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);">
                    View My Certificates
                </a>
            </div>
        </div>

        <!-- Footer -->
        <div style="background: #f9fafb; padding: 20px 28px; text-align: center; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 13px; margin: 0;">
                AuraLearn Team • Keep learning and growing
            </p>
            <p style="color: #d1d5db; font-size: 12px; margin: 6px 0 0 0;">
                This is an automated email. Please do not reply.
            </p>
        </div>
    </div>
    """

    attachments = None
    if pdf_path and os.path.exists(pdf_path):
        attachments = [
            (f"Certificate_{certificate_id}.pdf", pdf_path, "application/pdf")
        ]

    return send_email(subject, recipient, body, html_body, attachments=attachments)