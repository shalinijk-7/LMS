# Contains helper functions for generating and managing certificates.
import os
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from flask import current_app

def generate_certificate(student_name, course_name, issue_date=None):
    """
    Generates a PDF certificate and returns the certificate_id and relative file path.
    """
    if issue_date is None:
        issue_date = datetime.utcnow()
        
    certificate_id = str(uuid.uuid4().hex)[:12].upper()
    filename = f"cert_{certificate_id}.pdf"
    
    cert_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'certificates')
    os.makedirs(cert_dir, exist_ok=True)
    
    filepath = os.path.join(cert_dir, filename)
    
    # Create a canvas
    c = canvas.Canvas(filepath, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    # Add a border
    c.setStrokeColor(colors.HexColor('#2c3e50'))
    c.setLineWidth(10)
    c.rect(20, 20, width - 40, height - 40)
    c.setLineWidth(2)
    c.rect(26, 26, width - 52, height - 52)
    
    # Title
    c.setFont("Helvetica-Bold", 40)
    c.setFillColor(colors.HexColor('#2980b9'))
    c.drawCentredString(width / 2.0, height - 120, "Certificate of Completion")
    
    # Subtitle
    c.setFont("Helvetica", 20)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2.0, height - 180, "This is to certify that")
    
    # Student Name
    c.setFont("Helvetica-Bold", 35)
    c.setFillColor(colors.HexColor('#e74c3c'))
    c.drawCentredString(width / 2.0, height - 250, student_name)
    
    # Course details
    c.setFont("Helvetica", 20)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2.0, height - 310, "has successfully completed the course")
    
    c.setFont("Helvetica-Bold", 25)
    c.setFillColor(colors.HexColor('#2c3e50'))
    c.drawCentredString(width / 2.0, height - 360, course_name)
    
    # Date & ID
    c.setFont("Helvetica", 14)
    c.drawString(100, 100, f"Date: {issue_date.strftime('%B %d, %Y')}")
    c.drawString(100, 75, f"Certificate ID: {certificate_id}")
    
    # Signature line
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(width - 250, 100, width - 100, 100)
    c.drawCentredString(width - 175, 75, "Course Instructor")
    
    c.save()
    
    relative_path = f"/uploads/certificates/{filename}"
    return certificate_id, relative_path
