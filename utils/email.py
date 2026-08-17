import secrets
import string
from flask import current_app
from flask_mail import Message

# Assuming mail is initialized in app.py and imported where needed, or we can use current_app.extensions
def send_email(subject, recipient, body, html_body=None):
    """
    Sends an email using the Flask-Mail extension.
    
    Args:
        subject (str): The subject line of the email.
        recipient (str): The primary email address of the recipient.
        body (str): The plain text body of the email.
        html_body (str, optional): The HTML formatted body of the email. Defaults to None.
        
    Returns:
        bool: True if the email was sent successfully, False otherwise.
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
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        print(f"Fallback Logging - Subject: {subject}\nTo: {recipient}\nBody: {body}")
        return False

def generate_otp(length=6):
    """
    Generate a secure random numeric One-Time Password (OTP).
    
    Args:
        length (int): The number of digits for the OTP. Defaults to 6.
        
    Returns:
        str: A string containing the generated numeric OTP.
    """
    digits = string.digits
    return ''.join(secrets.choice(digits) for i in range(length))

def send_otp_email(recipient, otp):
    """
    Send a password reset OTP email to the user.
    
    Args:
        recipient (str): The email address of the user requesting the reset.
        otp (str): The generated One-Time Password.
        
    Returns:
        bool: True if sent successfully, False otherwise.
    """
    subject = "Your Password Reset OTP - LearnSphere AI"
    body = f"Hello,\n\nYour OTP for password reset is: {otp}\n\nThis OTP will expire in 10 minutes.\nIf you did not request this, please ignore this email.\n\nLearnSphere AI Team"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
        <h2 style="color: #2563EB;">Password Reset Request</h2>
        <p>Hello,</p>
        <p>We received a request to reset your password. Use the following One-Time Password (OTP) to proceed:</p>
        <div style="background-color: #f3f4f6; padding: 15px; text-align: center; border-radius: 8px; margin: 20px 0;">
            <h1 style="letter-spacing: 5px; color: #1f2937; margin: 0;">{otp}</h1>
        </div>
        <p style="color: #ef4444; font-size: 0.9em;">This OTP will expire in 10 minutes.</p>
        <p>If you did not request a password reset, please ignore this email or contact support.</p>
        <hr style="border: 0; border-top: 1px solid #e0e0e0; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 0.8em; text-align: center;">LearnSphere AI Team</p>
    </div>
    """
    
    return send_email(subject, recipient, body, html_body)

def send_2fa_otp_email(recipient, otp):
    """
    Send a Two-Factor Authentication (2FA) OTP email to the user.
    
    Args:
        recipient (str): The email address of the user attempting to log in.
        otp (str): The generated One-Time Password.
        
    Returns:
        bool: True if sent successfully, False otherwise.
    """
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
