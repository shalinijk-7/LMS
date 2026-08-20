import os
import logging
from flask import current_app
from flask_mail import Message
from app import mail

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
        
        # Need to fetch the latest certificate for the issue date
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
        
        # Resolve absolute path for the attachment
        if file_path.startswith('/'):
            file_path = file_path[1:] # remove leading slash
        
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
