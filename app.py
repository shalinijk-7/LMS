"""
Main application factory and configuration module for the LMS project.
Initializes Flask, sets up extensions (Database, Mail, OAuth, SocketIO),
and registers all application blueprints.
"""
import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO

mail = Mail()
oauth = OAuth()
socketio = SocketIO(cors_allowed_origins="*")

# Blueprints
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
from routes.payment import payment_bp

# Import socket events to register them
import routes.events

def create_app(config_class=Config):
    """
    Application factory function.
    
    Args:
        config_class (object): The configuration class to use (defaults to Config).
        
    Returns:
        Flask: The initialized Flask application instance.
    """
    app = Flask(__name__)
    # Load configuration settings from the provided config_class
    app.config.from_object(config_class)

    # Initialize Flask extensions with the app instance
    db.init_app(app)                     # Initialize SQLAlchemy database
    migrate = Migrate(app, db)           # Initialize Flask-Migrate for database migrations
    mail.init_app(app)                   # Initialize Flask-Mail for sending emails
    oauth.init_app(app)                  # Initialize Authlib OAuth client for SSO
    socketio.init_app(app)               # Initialize Flask-SocketIO for real-time communication
    
    # Register custom WebSocket events
    routes.events.register_events(socketio)
    
    # Register Google as an OAuth provider using configurations from app context
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
    
    # Configure Flask-Login for session management
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' # Redirect unauthorized users to the login route
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Flask-Login user loader callback.
        
        Args:
            user_id (str): The ID of the user to load.
            
        Returns:
            User: The User model instance if found, None otherwise.
        """
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_unread_counts():
        """
        Context processor to inject unread message and notification counts
        into all templates for the currently authenticated user.
        
        Returns:
            dict: A dictionary containing 'unread_messages_count' and 
                  'unread_notifications_count'.
        """
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
                
            return dict(unread_messages_count=dm_unread + course_unread, unread_notifications_count=notification_unread)
        return dict(unread_messages_count=0, unread_notifications_count=0)

    from routes.chat import chat_bp
    from routes.progress import progress_bp
    from routes.attendance import attendance_bp
    from routes.payment import payment_bp
    from routes.ai_routes import ai_bp

    # Register all modular Blueprints with the main application
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
    app.register_blueprint(payment_bp)
    app.register_blueprint(ai_bp)

    # Landing Page Route (since it's small, keeping it here for now)
    @app.route('/')
    def index():
        """
        Route for the application's landing page.
        
        Returns:
            str: Rendered HTML template for the landing page.
        """
        return render_template('landing/index.html')

    @app.route('/logout')
    def logout():
        """
        Common route to log out the user.
        """
        from flask_login import logout_user
        from flask import redirect, url_for, flash
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('auth.login'))

    @app.route('/terms')
    def terms():
        """Route for the Terms of Service page."""
        return render_template('legal/terms.html')

    @app.route('/privacy')
    def privacy():
        """Route for the Privacy Policy page."""
        return render_template('legal/privacy.html')

    from flask import send_from_directory
    @app.route('/sw.js')
    def sw():
        """
        Route to serve the Service Worker script for PWA support.
        
        Returns:
            Response: The sw.js file from the static directory.
        """
        return app.send_static_file('sw.js')

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """
        Route to serve user-uploaded files.
        
        Args:
            filename (str): The requested filename.
            
        Returns:
            Response: The requested file from the uploads directory.
        """
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Ensure instance folder and upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("\n" + "="*50)
    print("App is running! Click the link below to view it:")
    print("-> http://127.0.0.1:5000 <-")
    print("="*50 + "\n")
    
    socketio.run(app, debug=True)
