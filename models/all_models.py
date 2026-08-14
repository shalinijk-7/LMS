from . import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------------------------------------------
# USER & ROLES
# ----------------------------------------------------
class Role(db.Model):
    """
    Represents a user role (e.g., admin, instructor, student) in the system.
    """
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # admin, instructor, student
    users = db.relationship('User', backref='role', lazy=True)

class User(UserMixin, db.Model):
    """
    Represents a user in the system with authentication and profile details.
    """
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
    
    # 2FA fields
    two_factor_enabled = db.Column(db.Boolean, default=False)
    otp_hash = db.Column(db.String(255), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, default=0)
    otp_last_sent_at = db.Column(db.DateTime, nullable=True)
    
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
    """
    Stores user-specific settings and preferences, such as theme and notifications.
    """
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

class ActivityLog(db.Model):
    """
    Tracks user actions for auditing and analytics purposes.
    """
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------------------------------
# COURSE & LESSONS
# ----------------------------------------------------
class Category(db.Model):
    """
    Represents a course category for grouping related courses.
    """
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    courses = db.relationship('Course', backref='category', lazy=True)

class Course(db.Model):
    """
    Represents a course offered in the LMS, including metadata and relationships.
    """
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    thumbnail = db.Column(db.String(255))
    banner = db.Column(db.String(255))
    duration = db.Column(db.String(50))
    difficulty = db.Column(db.String(50)) # Beginner, Intermediate, Advanced
    course_type = db.Column(db.String(20), default='Free') # Free, Paid
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='USD')
    demo_video_title = db.Column(db.String(200), nullable=True)
    demo_video_url = db.Column(db.String(255), nullable=True)
    demo_video_file = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lessons = db.relationship('Lesson', backref='course', cascade='all, delete-orphan', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', cascade='all, delete-orphan', lazy=True)
    assignments = db.relationship('Assignment', backref='course', cascade='all, delete-orphan', lazy=True)
    quizzes = db.relationship('Quiz', backref='course', cascade='all, delete-orphan', lazy=True)
    discussion_threads = db.relationship('DiscussionThread', backref='course', cascade='all, delete-orphan', lazy=True)

class Enrollment(db.Model):
    """
    Links a student to a course they are enrolled in.
    """
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress_percent = db.Column(db.Integer, default=0)
    
class Progress(db.Model):
    """
    Tracks a student completion status for a specific lesson.
    """
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)

class Lesson(db.Model):
    """
    Represents a single lesson or module within a course.
    """
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    
    # Material relationships
    video = db.relationship('Video', backref='lesson', uselist=False, cascade='all, delete-orphan')
    materials = db.relationship('StudyMaterial', backref='lesson', cascade='all, delete-orphan', lazy=True)
    quizzes = db.relationship('Quiz', backref='lesson_ref', lazy=True)

class Video(db.Model):
    """
    Stores video URL and metadata for a lesson.
    """
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    url = db.Column(db.String(255), nullable=False)
    duration = db.Column(db.Integer) # in seconds

class StudyMaterial(db.Model):
    """
    Represents downloadable files (PDF, PPT) associated with a lesson.
    """
    __tablename__ = 'study_materials'
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20)) # pdf, ppt, etc.

# ----------------------------------------------------
# ASSIGNMENTS & QUIZZES
# ----------------------------------------------------
class Assignment(db.Model):
    """
    Represents an assignment given in a course with a deadline and marks.
    """
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    deadline = db.Column(db.DateTime)
    total_marks = db.Column(db.Integer)
    
    submissions = db.relationship('Submission', backref='assignment', cascade='all, delete-orphan', lazy=True)

class Submission(db.Model):
    """
    Represents a student submission for a specific assignment.
    """
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    marks_obtained = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    status = db.Column(db.String(50), default='Pending') # Pending, Graded

class Quiz(db.Model):
    """
    Represents a quiz associated with a course or lesson.
    """
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
    """
    Represents a single question within a quiz.
    """
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    
    answers = db.relationship('Answer', backref='question', cascade='all, delete-orphan', lazy=True)

class Answer(db.Model):
    """
    Represents a possible answer for a quiz question, indicating if it is correct.
    """
    __tablename__ = 'answers'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Result(db.Model):
    """
    Stores the final score of a student for a specific quiz.
    """
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------------------------------
# COMMUNICATION & NOTIFICATIONS
# ----------------------------------------------------
class DiscussionThread(db.Model):
    """
    Represents a top-level forum thread within a course.
    """
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
    """
    Represents a reply to a discussion thread.
    """
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
    """
    Stores notifications sent to users.
    """
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info') # info, success, warning, error
    icon = db.Column(db.String(50), default='bi-info-circle')
    action_url = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    
class LiveSession(db.Model):
    """
    Represents a scheduled live video session for a course.
    """
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
    """
    Represents a direct or group chat message between users.
    """
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Null for group chats
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True) # Set for group chats
    content = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.String(512), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_delivered = db.Column(db.Boolean, default=False)
    is_read = db.Column(db.Boolean, default=False)
    
    # Advanced Chat Features
    is_edited = db.Column(db.Boolean, default=False)
    is_deleted = db.Column(db.Boolean, default=False)
    is_pinned = db.Column(db.Boolean, default=False)
    is_announcement = db.Column(db.Boolean, default=False)
    reply_to_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    message_type = db.Column(db.String(20), default='text') # text, voice, file, image, video
    
    # Relationships
    reactions = db.relationship('MessageReaction', backref='message', lazy=True, cascade='all, delete-orphan')

class MessageReaction(db.Model):
    """
    Stores emoji reactions to chat messages.
    """
    __tablename__ = 'message_reactions'
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)

class CourseChatReadStatus(db.Model):
    """
    Tracks the last read message ID for a user in a course chat.
    """
    __tablename__ = 'course_chat_read_status'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    last_read_message_id = db.Column(db.Integer, nullable=False, default=0)

# ----------------------------------------------------
# OTHERS
# ----------------------------------------------------
class Certificate(db.Model):
    """
    Represents a certificate awarded to a student upon course completion.
    """
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_id = db.Column(db.String(100), unique=True, nullable=False)
    file_path = db.Column(db.String(255))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    
    course = db.relationship('Course', backref='course_certificates', lazy=True)

class Attendance(db.Model):
    """
    Tracks student attendance for live sessions or physical classes.
    """
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20)) # Present, Absent, Late
    remarks = db.Column(db.Text, nullable=True)

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    lesson = db.relationship('Lesson', foreign_keys=[lesson_id])

class StudentProgress(db.Model):
    """
    Provides aggregated progress metrics for a student in a course.
    """
    __tablename__ = 'student_progress'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    progress_percentage = db.Column(db.Integer, default=0)
    lessons_completed = db.Column(db.Integer, default=0)
    total_lessons = db.Column(db.Integer, default=0)
    learning_time = db.Column(db.Integer, default=0) # in minutes
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Not Started') # Not Started, In Progress, Completed

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    lesson = db.relationship('Lesson', foreign_keys=[lesson_id])

class CourseCompletion(db.Model):
    """
    Records when a student fully completes a course.
    """
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
    """
    Represents a payment transaction made by a student for a course.
    """
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='USD')
    payment_method = db.Column(db.String(50), nullable=False)
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Pending') # Pending, Success, Failed
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])

class PurchaseHistory(db.Model):
    """
    Links a payment to a student and course for record-keeping.
    """
    __tablename__ = 'purchase_history'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    payment = db.relationship('Payment', foreign_keys=[payment_id])

# ----------------------------------------------------
# AI FEATURES
# ----------------------------------------------------
class AIChatMessage(db.Model):
    __tablename__ = 'ai_chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'user' or 'model'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])

class AISummary(db.Model):
    __tablename__ = 'ai_summaries'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summary_text = db.Column(db.Text, nullable=False)
    summary_type = db.Column(db.String(50), nullable=False) # Short, Medium, Detailed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
