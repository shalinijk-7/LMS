# Initializes the routes package for the Flask application.
from . import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Stores different user roles like Admin, Instructor, and Student.
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # admin, instructor, student
    users = db.relationship('User', backref='role', lazy=True)


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text)
    profile_photo = db.Column(db.String(255), default='default.jpg')
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    settings = db.relationship('Setting', backref='user', uselist=False, cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    courses_taught = db.relationship('Course', backref='instructor', lazy=True)
    submissions = db.relationship('Submission', backref='student', lazy=True)
    quiz_results = db.relationship('Result', backref='student', lazy=True)
    certificates = db.relationship('Certificate', backref='student', lazy=True)
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(20), default='en')
    notification_prefs = db.Column(db.Boolean, default=True)
    notification_sound_enabled = db.Column(db.Boolean, default=True)
    desktop_notifications_enabled = db.Column(db.Boolean, default=False)
    real_time_notifications_enabled = db.Column(db.Boolean, default=True)
    email_notifications_enabled = db.Column(db.Boolean, default=True)
    two_factor_enabled = db.Column(db.Boolean, default=False)


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    courses = db.relationship('Course', backref='category', lazy=True)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    thumbnail = db.Column(db.String(255))
    banner = db.Column(db.String(255))
    duration = db.Column(db.String(50))
    difficulty = db.Column(db.String(50))  # Beginner, Intermediate, Advanced
    price = db.Column(db.Float, default=0.0)
    demo_video_title = db.Column(db.String(200))      # ← NEW
    demo_video_url = db.Column(db.String(500))        # ← NEW
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lessons = db.relationship('Lesson', backref='course', cascade='all, delete-orphan', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', cascade='all, delete-orphan', lazy=True)
    assignments = db.relationship('Assignment', backref='course', cascade='all, delete-orphan', lazy=True)
    quizzes = db.relationship('Quiz', backref='course', cascade='all, delete-orphan', lazy=True)
    discussion_threads = db.relationship('DiscussionThread', backref='course', cascade='all, delete-orphan', lazy=True)


class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress_percent = db.Column(db.Integer, default=0)


class Progress(db.Model):
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)


class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)

    video = db.relationship('Video', backref='lesson', uselist=False, cascade='all, delete-orphan')
    materials = db.relationship('StudyMaterial', backref='lesson', cascade='all, delete-orphan', lazy=True)
    quizzes = db.relationship('Quiz', backref='lesson_ref', lazy=True)


class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer)  # in seconds


class StudyMaterial(db.Model):
    __tablename__ = 'study_materials'
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20))


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    total_marks = db.Column(db.Integer)

    submissions = db.relationship('Submission', backref='assignment', cascade='all, delete-orphan', lazy=True)


class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    marks_obtained = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending')


class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    timer_minutes = db.Column(db.Integer, default=30)
    start_date = db.Column(db.DateTime, nullable=True)
    expiry_date = db.Column(db.DateTime, nullable=True)

    questions = db.relationship('Question', backref='quiz', cascade='all, delete-orphan', lazy=True)
    results = db.relationship('Result', backref='quiz', cascade='all, delete-orphan', lazy=True)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)

    answers = db.relationship('Answer', backref='question', cascade='all, delete-orphan', lazy=True)


class Answer(db.Model):
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class DiscussionThread(db.Model):
    __tablename__ = 'discussion_threads'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='threads')
    replies = db.relationship('DiscussionReply', backref='thread', cascade='all, delete-orphan', lazy=True)


class DiscussionReply(db.Model):
    __tablename__ = 'discussion_replies'
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('discussion_threads.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_best_answer = db.Column(db.Boolean, default=False)
    likes = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref='discussion_replies')


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')
    icon = db.Column(db.String(50), default='bi-info-circle')
    action_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id])


class LiveSession(db.Model):
    __tablename__ = 'live_sessions'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    meeting_link = db.Column(db.String(512), nullable=False)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref='live_sessions')
    instructor = db.relationship('User', backref='live_sessions')


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(512), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_delivered = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)

    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_announcement = db.Column(db.Boolean, default=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    message_type = db.Column(db.String(20), default='text')

    reactions = db.relationship('MessageReaction', backref='message', lazy=True, cascade='all, delete-orphan')


class MessageReaction(db.Model):
    __tablename__ = 'message_reactions'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)


class CourseChatReadStatus(db.Model):
    __tablename__ = 'course_chat_read_status'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    last_read_message_id = db.Column(db.Integer, nullable=False, default=0)


class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_id = db.Column(db.String(100), unique=True, nullable=False)
    file_path = db.Column(db.String(255))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship('Course', backref='course_certificates', lazy=True)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20))
    remarks = db.Column(db.Text, nullable=True)

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    lesson = db.relationship('Lesson', foreign_keys=[lesson_id])


class StudentProgress(db.Model):
    __tablename__ = 'student_progress'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    progress_percentage = db.Column(db.Integer, default=0)
    lessons_completed = db.Column(db.Integer, default=0)
    total_lessons = db.Column(db.Integer, default=0)
    learning_time = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Not Started')

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    lesson = db.relationship('Lesson', foreign_keys=[lesson_id])


class CourseCompletion(db.Model):
    __tablename__ = 'course_completion'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    completion_date = db.Column(db.DateTime, default=datetime.utcnow)
    certificate_status = db.Column(db.String(50), default='Not Issued')
    completion_percentage = db.Column(db.Integer, default=100)

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(30), default='Pending')
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', foreign_keys=[student_id], backref='payments')
    course = db.relationship('Course', foreign_keys=[course_id], backref='payments')