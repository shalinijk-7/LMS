from app import create_app
from models import db
from models.course import Course
from models.user import User

app = create_app()

with app.app_context():
    # Make sure we have an instructor
    instructor = User.query.filter_by(role='instructor').first()
    if not instructor:
        instructor = User(first_name='Dr.', last_name='Smith', email='drsmith@example.com', role='instructor')
        instructor.set_password('password123')
        db.session.add(instructor)
        db.session.commit()

    # Add sample courses
    courses = [
        Course(
            title="Advanced Python Masterclass",
            description="Deep dive into Python programming. Learn advanced concepts like decorators, generators, context managers, and concurrency.",
            price=49.99,
            instructor_id=instructor.id
        ),
        Course(
            title="Data Science with Pandas and NumPy",
            description="Learn how to analyze data, create visualizations, and extract insights using Python's most popular data science libraries.",
            price=59.99,
            instructor_id=instructor.id
        ),
        Course(
            title="Web Development Bootcamp",
            description="Become a full-stack web developer. Learn HTML, CSS, JavaScript, React, and Node.js from scratch.",
            price=89.99,
            instructor_id=instructor.id
        ),
        Course(
            title="UI/UX Design Fundamentals",
            description="Master the art of creating beautiful, user-centric interfaces using Figma and modern design principles.",
            price=39.99,
            instructor_id=instructor.id
        )
    ]
    
    for course in courses:
        # Check if already exists
        if not Course.query.filter_by(title=course.title).first():
            db.session.add(course)
            
    db.session.commit()
    print("Seed data inserted successfully!")
