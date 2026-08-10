# Main application file that initializes and runs the Flask LMS application.
import os
from flask import Flask, render_template, flash, request, redirect, url_for
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO

# Initialize extensions
mail = Mail()          # mails
oauth = OAuth()        # google login
socketio = SocketIO(cors_allowed_origins="*")  # for real time chat

# Blueprints importing
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.instructor import instructor_bp
from routes.student import student_bp
from routes.settings import settings_bp
from routes.dashboard import dashboard_bp
from routes.courses import courses_bp
from routes.quiz import quiz_bp
from routes.assignment import assignment_bp
from routes.certificate import certificate_bp
from routes.discussion import discussion_bp
from routes.notifications import notifications_bp
from routes.analytics import analytics_bp
from routes.chat import chat_bp
from routes.progress import progress_bp
from routes.attendance import attendance_bp

# Import socket events to register them
import routes.events

def create_app(config_class=Config):
    """
    Creates and configures the Flask application.

    This function initializes all Flask extensions, registers
    blueprints, configures authentication, Socket.IO, Google OAuth,
    context processors, and application routes.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)
    oauth.init_app(app)
    socketio.init_app(app)
    routes.events.register_events(socketio)

    # Configure Google OAuth Login
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile',
            'verify': False
        }
    )

    # Configure Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Loads the logged-in user from the database using their user ID.
        Flask-Login calls this function automatically to restore the user's session.
        """
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_unread_counts():
        # Counts unread messages and notifications for the logged-in user
        from flask_login import current_user
        if current_user.is_authenticated:
            from models import Message, CourseChatReadStatus, Course, Notification
            
            dm_unread = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
            
            course_unread = 0
            courses = []
            if current_user.role.name == 'student':
                courses = [e.course for e in current_user.enrollments if e.course]
            elif current_user.role.name == 'instructor':
                courses = Course.query.filter_by(instructor_id=current_user.id).all()
                
            for course in courses:
                status = CourseChatReadStatus.query.filter_by(user_id=current_user.id, course_id=course.id).first()
                last_id = status.last_read_message_id if status else 0
                count = Message.query.filter_by(course_id=course.id).filter(Message.id > last_id).count()
                course_unread += count
                
            notification_unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
                
            return dict(
                unread_messages_count=dm_unread + course_unread,
                unread_notifications_count=notification_unread
            )
        return dict(unread_messages_count=0, unread_notifications_count=0)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(instructor_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(assignment_bp)
    app.register_blueprint(certificate_bp)
    app.register_blueprint(discussion_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(attendance_bp)

    # ====================== LANDING PAGE ROUTES ======================

    @app.route('/')
    def index():
        return render_template('landing/index.html')

    @app.route('/terms')
    def terms():
        return render_template('landing/terms.html')

    @app.route('/privacy')
    def privacy():
        return render_template('landing/privacy.html')

    @app.route('/help')
    def help_center():
        return render_template('landing/help.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            subject = request.form.get('subject', '').strip()
            message = request.form.get('message', '').strip()

            if not name or not email or not subject or not message:
                flash('Please fill in all fields.', 'danger')
                return render_template('landing/contact.html')

            # Success message
            flash('Thank you! Your message has been received. Our team will get back to you within 24 hours.', 'success')
            return redirect(url_for('contact'))

        return render_template('landing/contact.html')

    # ====================== OTHER ROUTES ======================

    from flask import send_from_directory

    @app.route('/sw.js')
    def sw():
        return app.send_static_file('sw.js')

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Ensure instance folder and upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app


app = create_app()

if __name__ == '__main__':
    # Create database tables if they do not already exist
    with app.app_context():
        db.create_all()
    
    print("\n" + "="*50)
    print("App is running! Click the link below to view it:")
    print("-> http://127.0.0.1:5000 <-")
    print("="*50 + "\n")

    # Start the Flask application with Socket.IO support
    socketio.run(app, debug=True)