import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth

mail = Mail()
oauth = OAuth()

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

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    mail.init_app(app)
    oauth.init_app(app)
    
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
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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

    # Landing Page Route (since it's small, keeping it here for now)
    @app.route('/')
    def index():
        return render_template('landing/index.html')

    # Ensure instance folder and upload folders exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
