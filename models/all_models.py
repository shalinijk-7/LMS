# Import the database instance from the current application package
from . import db
# Import datetime utility for managing record timestamps
from datetime import datetime
# Import UserMixin to supply standard Flask-Login implementations
from flask_login import UserMixin
# Import security helpers for secure password hashing and verification
from werkzeug.security import generate_password_hash, check_password_hash

# ==============================================================================
# USER & ROLES MODULE
# ==============================================================================

class Role(db.Model):
    """
    Represents a user role (e.g., admin, instructor, student) in the system.
    Determines administrative and feature permissions across the platform.
    """
    __tablename__ = 'roles'
    
    # Primary identifier for roles
    id = db.Column(db.Integer, primary_key=True)
    # Unique role name used for authorization checks
    name = db.Column(db.String(50), unique=True, nullable=False) # admin, instructor, student
    # One-to-many relationship tracking all users assigned to this role
    users = db.relationship('User', backref='role', lazy=True)

class User(UserMixin, db.Model):
    """
    Represents a user in the system with authentication and profile details.
    Handles general access, profile fields, and two-factor authentication (2FA).
    """
    __tablename__ = 'users'
    
    # Primary user identifiers and basic profile details
    # Primary key identifier for the user
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key linking the user to a specific role
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    # Full name of the user
    name = db.Column(db.String(100), nullable=False)
    # Email address of the user, used for login and notifications
    email = db.Column(db.String(120), unique=True, nullable=False)
    # Optional phone number for contact or 2FA
    phone = db.Column(db.String(20))
    # Securely hashed password string
    password_hash = db.Column(db.String(255), nullable=False)
    # Short biography or description provided by the user
    bio = db.Column(db.Text)
    # File path or URL to the user's profile photo
    profile_photo = db.Column(db.String(255), default='default.jpg')
    # Flag indicating whether the user's email or account is verified
    is_verified = db.Column(db.Boolean, default=False)
    # Timestamp of when the user account was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 2FA (Two-Factor Authentication) security credentials
    two_factor_enabled = db.Column(db.Boolean, default=False)
    otp_hash = db.Column(db.String(255), nullable=True)
    otp_expires_at = db.Column(db.DateTime, nullable=True)
    otp_attempts = db.Column(db.Integer, default=0)
    otp_last_sent_at = db.Column(db.DateTime, nullable=True)
    
    # Database relationships mapping user activities and records
    settings = db.relationship('Setting', backref='user', uselist=False, cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    courses_taught = db.relationship('Course', backref='instructor', lazy=True)
    submissions = db.relationship('Submission', backref='student', lazy=True)
    quiz_results = db.relationship('Result', backref='student', lazy=True)
    certificates = db.relationship('Certificate', backref='student', lazy=True)
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy=True)
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

    def set_password(self, password):
        """
        Generates and assigns a secure hash from the provided plain text password.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Verifies if the provided plain text password matches the stored hash.
        """
        return check_password_hash(self.password_hash, password)

class Setting(db.Model):
    """
    Stores user-specific settings and preferences, such as theme and notifications.
    Keeps application UI choices and messaging channels customizable per user.
    """
    __tablename__ = 'settings'
    
    # Primary key identifier for the settings record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the user these settings belong to
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # General localization and visual styling configurations
    theme = db.Column(db.String(20), default='light')
    language = db.Column(db.String(20), default='en')
    
    # Notification delivery channel toggle settings
    notification_prefs = db.Column(db.Boolean, default=True)
    notification_sound_enabled = db.Column(db.Boolean, default=True)
    desktop_notifications_enabled = db.Column(db.Boolean, default=False)
    real_time_notifications_enabled = db.Column(db.Boolean, default=True)
    email_notifications_enabled = db.Column(db.Boolean, default=True)

class ActivityLog(db.Model):
    """
    Tracks user actions for auditing and analytics purposes.
    Keeps security records of major administrative or profile actions.
    """
    __tablename__ = 'activity_logs'
    
    # Primary key identifier for the activity log entry
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the user who performed the action
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Description of the action performed
    action = db.Column(db.String(255), nullable=False)
    # Timestamp when the action was recorded
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ==============================================================================
# COURSE & LESSONS MODULE
# ==============================================================================

class Category(db.Model):
    """
    Represents a course category for grouping related courses.
    Allows students to search and filter learning contents by subject domain.
    """
    __tablename__ = 'categories'
    
    # Primary key identifier for the category
    id = db.Column(db.Integer, primary_key=True)
    # Unique name of the category (e.g., Programming, Design)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Relationship to the courses within this category
    courses = db.relationship('Course', backref='category', lazy=True)

class Course(db.Model):
    """
    Represents a course offered in the LMS, including metadata and relationships.
    Forms the structural parent container for all lessons, materials, quizzes, and discussion threads.
    """
    __tablename__ = 'courses'
    
    # Primary key identifier for the course
    id = db.Column(db.Integer, primary_key=True)
    # Title or name of the course
    title = db.Column(db.String(200), nullable=False)
    # Detailed description of the course content
    description = db.Column(db.Text, nullable=False)
    # Foreign key referencing the instructor who created or manages the course
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the category this course belongs to
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Course media attachments and branding
    thumbnail = db.Column(db.String(255))
    banner = db.Column(db.String(255))
    
    # Metadata detailing the depth and target group of the course
    duration = db.Column(db.String(50))
    difficulty = db.Column(db.String(50)) # Beginner, Intermediate, Advanced
    
    # Payment status attributes
    course_type = db.Column(db.String(20), default='Free') # Free, Paid
    price = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default='USD')
    
    # Optional introductory preview video configurations
    demo_video_title = db.Column(db.String(200), nullable=True)
    demo_video_url = db.Column(db.String(255), nullable=True)
    demo_video_file = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Core structural relationships with automatic cascade-deletion triggers
    lessons = db.relationship('Lesson', backref='course', cascade='all, delete-orphan', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', cascade='all, delete-orphan', lazy=True)
    assignments = db.relationship('Assignment', backref='course', cascade='all, delete-orphan', lazy=True)
    quizzes = db.relationship('Quiz', backref='course', cascade='all, delete-orphan', lazy=True)
    discussion_threads = db.relationship('DiscussionThread', backref='course', cascade='all, delete-orphan', lazy=True)

class Enrollment(db.Model):
    """
    Links a student to a course they are enrolled in.
    Serves as an association mapping with enrollment progress records.
    """
    __tablename__ = 'enrollments'
    
    # Primary key identifier for the enrollment record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the enrolled user (student)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the course the user is enrolled in
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Timestamp of when the enrollment occurred
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Percentage of course completed by the student
    progress_percent = db.Column(db.Integer, default=0)
    
class Progress(db.Model):
    """
    Tracks a student completion status for a specific lesson.
    Used for modular monitoring of student course navigation.
    """
    __tablename__ = 'progress'
    
    # Primary key identifier for the progress record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the lesson being tracked
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    # Boolean flag indicating if the lesson has been completed
    completed = db.Column(db.Boolean, default=False)
    # Timestamp of when the lesson was completed
    completed_at = db.Column(db.DateTime)

class Lesson(db.Model):
    """
    Represents a single lesson or module within a course.
    Acts as the target entity for study materials, videos, and inline structured quizzes.
    """
    __tablename__ = 'lessons'
    
    # Primary key identifier for the lesson
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the course this lesson belongs to
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Title of the lesson
    title = db.Column(db.String(200), nullable=False)
    # Optional description or notes for the lesson
    description = db.Column(db.Text)
    # Index to determine the order of the lesson within the course
    order_index = db.Column(db.Integer, default=0)
    
    # Associated study resources and components
    video = db.relationship('Video', backref='lesson', uselist=False, cascade='all, delete-orphan')
    materials = db.relationship('StudyMaterial', backref='lesson', cascade='all, delete-orphan', lazy=True)
    quizzes = db.relationship('Quiz', backref='lesson_ref', lazy=True)

class Video(db.Model):
    """
    Stores video URL and metadata for a lesson.
    Integrates streaming links directly inside structured lesson schedules.
    """
    __tablename__ = 'videos'
    
    # Primary key identifier for the video record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the associated lesson
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    # URL to the video content (e.g., streaming link or hosted file)
    url = db.Column(db.String(255), nullable=False)
    # Duration of the video in seconds
    duration = db.Column(db.Integer) # in seconds

class StudyMaterial(db.Model):
    """
    Represents downloadable files (PDF, PPT) associated with a lesson.
    Stores file system resource locations for student reference download files.
    """
    __tablename__ = 'study_materials'
    
    # Primary key identifier for the study material
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the lesson this material belongs to
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    # Title or name of the study material file
    title = db.Column(db.String(200), nullable=False)
    # File system path or URL where the material is stored
    file_path = db.Column(db.String(255), nullable=False)
    # Extension or type of the file (e.g., pdf, ppt)
    file_type = db.Column(db.String(20)) # pdf, ppt, etc.

# ==============================================================================
# ASSIGNMENTS & QUIZZES MODULE
# ==============================================================================

class Assignment(db.Model):
    """
    Represents an assignment given in a course with a deadline and marks.
    Defines practical evaluation parameters for homework tasks.
    """
    __tablename__ = 'assignments'
    
    # Primary key identifier for the assignment
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the course the assignment belongs to
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Title of the assignment
    title = db.Column(db.String(200), nullable=False)
    # Detailed description and instructions for the assignment
    description = db.Column(db.Text)
    # Due date and time for the assignment submission
    deadline = db.Column(db.DateTime)
    # Maximum possible marks achievable for the assignment
    total_marks = db.Column(db.Integer)
    
    # Relationship monitoring student submissions for this assignment
    submissions = db.relationship('Submission', backref='assignment', cascade='all, delete-orphan', lazy=True)

class Submission(db.Model):
    """
    Represents a student submission for a specific assignment.
    Records delivery dates, grades obtained, and feedback from instructors.
    """
    __tablename__ = 'submissions'
    
    # Primary key identifier for the submission
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the assignment being submitted
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    # Foreign key referencing the student making the submission
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # File path to the uploaded submission document
    file_path = db.Column(db.String(255), nullable=False)
    # Timestamp of when the submission was made
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Marks awarded to the submission by the instructor
    marks_obtained = db.Column(db.Integer)
    # Optional feedback provided by the instructor
    feedback = db.Column(db.Text)
    # Grading status of the submission (e.g., Pending, Graded)
    status = db.Column(db.String(50), default='Pending') # Pending, Graded

class Quiz(db.Model):
    """
    Represents a quiz associated with a course or lesson.
    Manages quiz access dates, testing durations, and relationship hierarchies.
    """
    __tablename__ = 'quizzes'
    
    # Primary key identifier for the quiz
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the course the quiz belongs to
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Optional foreign key referencing a specific lesson for inline quizzes
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    # Title of the quiz
    title = db.Column(db.String(200), nullable=False)
    # Time limit for the quiz in minutes
    timer_minutes = db.Column(db.Integer, default=30)
    # Date and time when the quiz becomes accessible
    start_date = db.Column(db.DateTime, nullable=True)
    # Date and time when the quiz access expires
    expiry_date = db.Column(db.DateTime, nullable=True)
    
    # AI Practice feature
    is_ai_generated = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Linked nested components for question composition and grading outcomes
    questions = db.relationship('Question', backref='quiz', cascade='all, delete-orphan', lazy=True)
    results = db.relationship('Result', backref='quiz', cascade='all, delete-orphan', lazy=True)

class Question(db.Model):
    """
    Represents a single question within a quiz.
    Stores the core textual query and binds a collection of optional choices.
    """
    __tablename__ = 'questions'
    
    # Primary key identifier for the question
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the quiz this question belongs to
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    # The actual text or content of the question
    text = db.Column(db.Text, nullable=False)
    # Explanation for AI-generated practice questions
    explanation = db.Column(db.Text, nullable=True)
    
    # Choices relationship mapping
    answers = db.relationship('Answer', backref='question', cascade='all, delete-orphan', lazy=True)

class Answer(db.Model):
    """
    Represents a possible answer for a quiz question, indicating if it is correct.
    Utilized to automatically score responses upon submission.
    """
    __tablename__ = 'answers'
    
    # Primary key identifier for the answer choice
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the associated question
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    # Text content of the answer choice
    text = db.Column(db.String(255), nullable=False)
    # Boolean flag indicating if this is the correct answer
    is_correct = db.Column(db.Boolean, default=False)

class Result(db.Model):
    """
    Stores the final score of a student for a specific quiz.
    Maintains historic evidence of evaluation performances.
    """
    __tablename__ = 'results'
    
    # Primary key identifier for the quiz result
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the quiz taken
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    # Foreign key referencing the student who took the quiz
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # The student's obtained score
    score = db.Column(db.Integer, nullable=False)
    # The total possible score for the quiz
    total = db.Column(db.Integer, nullable=False)
    # Timestamp of when the quiz was submitted
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==============================================================================
# COMMUNICATION & NOTIFICATIONS MODULE
# ==============================================================================

class DiscussionThread(db.Model):
    """
    Represents a top-level forum thread within a course.
    Enables collaborative questions, pinned highlights, and locking systems.
    """
    __tablename__ = 'discussion_threads'
    
    # Primary key identifier for the discussion thread
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the course where the thread is posted
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Foreign key referencing the user who created the thread
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Title or subject of the discussion thread
    title = db.Column(db.String(200), nullable=False)
    # Main content or body of the thread
    content = db.Column(db.Text, nullable=False)
    # Timestamp of when the thread was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Boolean flag indicating if the thread is pinned to the top
    is_pinned = db.Column(db.Boolean, default=False)
    # Boolean flag indicating if the thread is closed to new replies
    is_locked = db.Column(db.Boolean, default=False)
    
    # Back-relations for user tracking and responses grouping
    user = db.relationship('User', backref='threads')
    replies = db.relationship('DiscussionReply', backref='thread', cascade='all, delete-orphan', lazy=True)

class DiscussionReply(db.Model):
    """
    Represents a reply to a discussion thread.
    Features social interaction configurations like system upvotes and marked best answers.
    """
    __tablename__ = 'discussion_replies'
    
    # Primary key identifier for the discussion reply
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the parent discussion thread
    thread_id = db.Column(db.Integer, db.ForeignKey('discussion_threads.id'), nullable=False)
    # Foreign key referencing the user who posted the reply
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Content of the reply message
    content = db.Column(db.Text, nullable=False)
    # Timestamp of when the reply was posted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Boolean flag indicating if this reply was marked as the best answer
    is_best_answer = db.Column(db.Boolean, default=False)
    # Count of likes or upvotes received by the reply
    likes = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref='discussion_replies')

class Notification(db.Model):
    """
    Stores notifications sent to users.
    Powers internal alert systems, linking icons, target screens, and state updates.
    """
    __tablename__ = 'notifications'
    
    # Primary key identifier for the notification
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the user receiving the notification
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the user who triggered the notification
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # Title or subject of the notification
    title = db.Column(db.String(255), nullable=False)
    # Main body content of the notification message
    message = db.Column(db.Text, nullable=False)
    # Type of notification (e.g., info, success, warning, error)
    notification_type = db.Column(db.String(50), default='info') # info, success, warning, error
    # Visual icon identifier for the notification display
    icon = db.Column(db.String(50), default='bi-info-circle')
    # Optional URL to redirect the user when clicked
    action_url = db.Column(db.String(255), nullable=True)
    # Boolean flag indicating if the user has read the notification
    is_read = db.Column(db.Boolean, default=False)
    # Timestamp of when the notification was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sender = db.relationship('User', foreign_keys=[sender_id])
    
class LiveSession(db.Model):
    """
    Represents a scheduled live video session for a course.
    Keeps trace of remote learning links, physical/virtual date planning, and organizers.
    """
    __tablename__ = 'live_sessions'
    
    # Primary key identifier for the live session
    id = db.Column(db.Integer, primary_key=True)
    # Title or topic of the live session
    title = db.Column(db.String(255), nullable=False)
    # Foreign key referencing the associated course
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Foreign key referencing the instructor hosting the session
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # External URL or link to join the meeting
    meeting_link = db.Column(db.String(512), nullable=False)
    # Date and time when the session is scheduled to begin
    scheduled_date = db.Column(db.DateTime, nullable=False)
    # Boolean flag indicating if this is a recurring session
    is_recurring = db.Column(db.Boolean, default=False)
    # Timestamp of when the session was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    course = db.relationship('Course', backref='live_sessions')
    instructor = db.relationship('User', backref='live_sessions')

class Message(db.Model):
    """
    Represents a direct or group chat message between users.
    Supplements real-time communication with files, pinned setups, edits, and parent replies.
    """
    __tablename__ = 'messages'
    
    # Primary key identifier for the message
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the user who sent the message
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the user receiving the message (Null for group chats)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Null for group chats
    # Foreign key referencing the course (Set for group chats)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True) # Set for group chats
    # Main text content of the message
    content = db.Column(db.Text, nullable=False)
    # Optional URL to an attached file or media
    file_url = db.Column(db.String(512), nullable=True)
    # Timestamp of when the message was sent
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Flag indicating if the message has been delivered to the recipient
    is_delivered = db.Column(db.Boolean, default=False)
    # Flag indicating if the message has been read by the recipient
    is_read = db.Column(db.Boolean, default=False)
    
    # Advanced Chat Features
    # Flag indicating if the message was edited after sending
    is_edited = db.Column(db.Boolean, default=False)
    # Flag indicating if the message was deleted by the sender
    is_deleted = db.Column(db.Boolean, default=False)
    # Flag indicating if the message is pinned in the chat
    is_pinned = db.Column(db.Boolean, default=False)
    # Flag indicating if the message is an announcement
    is_announcement = db.Column(db.Boolean, default=False)
    # Foreign key referencing a parent message this is replying to
    reply_to_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    # Type of the message (e.g., text, voice, file, image, video)
    message_type = db.Column(db.String(20), default='text') # text, voice, file, image, video
    
    # Relationships
    reactions = db.relationship('MessageReaction', backref='message', lazy=True, cascade='all, delete-orphan')

class MessageReaction(db.Model):
    """
    Stores emoji reactions to chat messages.
    Tracks user interaction choices applied directly to messaging streams.
    """
    __tablename__ = 'message_reactions'
    
    # Primary key identifier for the reaction
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the message being reacted to
    message_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=False)
    # Foreign key referencing the user who reacted
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # The emoji character used for the reaction
    emoji = db.Column(db.String(10), nullable=False)

class CourseChatReadStatus(db.Model):
    """
    Tracks the last read message ID for a user in a course chat.
    Enables accurate unseen-message badges across multi-user structures.
    """
    __tablename__ = 'course_chat_read_status'
    
    # Primary key identifier for the read status record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the user
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the course chat
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # ID of the last message read by the user in this chat
    last_read_message_id = db.Column(db.Integer, nullable=False, default=0)

# ==============================================================================
# PROGRESS, CERTIFICATES, & SALES MODULE
# ==============================================================================

class Certificate(db.Model):
    """
    Represents a certificate awarded to a student upon course completion.
    Logs delivery reports and system storage file paths for verification.
    """
    __tablename__ = 'certificates'
    
    # Primary key identifier for the certificate record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student who earned the certificate
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the course completed
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Unique identifier string for certificate verification
    certificate_id = db.Column(db.String(100), unique=True, nullable=False)
    # File system path or URL to the generated certificate PDF
    file_path = db.Column(db.String(255))
    # Timestamp of when the certificate was issued
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Boolean flag indicating if the certificate was emailed to the student
    email_sent = db.Column(db.Boolean, default=False)
    # Timestamp of when the email was dispatched
    email_sent_at = db.Column(db.DateTime, nullable=True)
    
    course = db.relationship('Course', backref='course_certificates', lazy=True)

class Attendance(db.Model):
    """
    Tracks student attendance for live sessions or physical classes.
    Maintains chronological records of active student participation.
    """
    __tablename__ = 'attendance'
    
    # Primary key identifier for the attendance record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the associated course
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Optional foreign key for a specific lesson or session
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    # Foreign key referencing the instructor who marked attendance
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # Date of the attendance record
    attendance_date = db.Column(db.Date, nullable=False)
    # Status of attendance (e.g., Present, Absent, Late)
    status = db.Column(db.String(20)) # Present, Absent, Late
    # Optional remarks or notes regarding the student's attendance
    remarks = db.Column(db.Text, nullable=True)

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    lesson = db.relationship('Lesson', foreign_keys=[lesson_id])

class StudentProgress(db.Model):
    """
    Provides aggregated progress metrics for a student in a course.
    Monitors overall lesson tracking, timeline completion rates, and learning active metrics.
    """
    __tablename__ = 'student_progress'
    
    # Primary key identifier for the student progress record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the course being tracked
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Optional foreign key referencing the currently active lesson
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=True)
    # Overall percentage of the course completed
    progress_percentage = db.Column(db.Integer, default=0)
    # Number of lessons successfully completed
    lessons_completed = db.Column(db.Integer, default=0)
    # Total number of lessons in the course at the time of tracking
    total_lessons = db.Column(db.Integer, default=0)
    # Total accumulated learning time in minutes
    learning_time = db.Column(db.Integer, default=0) # in minutes
    # Timestamp of the last time the student accessed the course
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    # High-level status of the student's progress (e.g., Not Started, In Progress, Completed)
    status = db.Column(db.String(50), default='Not Started') # Not Started, In Progress, Completed

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    lesson = db.relationship('Lesson', foreign_keys=[lesson_id])

class CourseCompletion(db.Model):
    """
    Records when a student fully completes a course.
    Triggers and traces automated credential generation and validation checks.
    """
    __tablename__ = 'course_completion'
    
    # Primary key identifier for the course completion record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student who completed the course
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the completed course
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Timestamp of when the course was successfully completed
    completion_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Status indicating if a certificate has been generated or issued
    certificate_status = db.Column(db.String(50), default='Not Issued')
    # Percentage of course finished, typically 100 upon completion
    completion_percentage = db.Column(db.Integer, default=100)

    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])

class Payment(db.Model):
    """
    Represents a payment transaction made by a student for a course.
    Captures financial tokens, transactional identifiers, and payment states.
    """
    __tablename__ = 'payments'
    
    # Primary key identifier for the payment record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student making the payment
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the course being purchased
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # The financial amount paid for the course
    amount = db.Column(db.Float, nullable=False)
    # The currency used for the payment (e.g., USD)
    currency = db.Column(db.String(10), default='USD')
    # The method or gateway used for the payment (e.g., Credit Card, PayPal)
    payment_method = db.Column(db.String(50), nullable=False)
    # Unique identifier provided by the payment gateway for the transaction
    transaction_id = db.Column(db.String(100), unique=True, nullable=False)
    # Current status of the payment (e.g., Pending, Success, Failed)
    status = db.Column(db.String(20), default='Pending') # Pending, Success, Failed
    # Timestamp of when the payment was processed
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])

class PurchaseHistory(db.Model):
    """
    Links a payment to a student and course for record-keeping.
    Provides audited verification lines mapping financial checkout receipts to users.
    """
    __tablename__ = 'purchase_history'
    
    # Primary key identifier for the purchase history record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student who made the purchase
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Foreign key referencing the purchased course
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    # Foreign key referencing the associated payment transaction
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=False)
    # Timestamp of when the purchase was finalized
    purchase_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])
    course = db.relationship('Course', foreign_keys=[course_id])
    payment = db.relationship('Payment', foreign_keys=[payment_id])

# ==============================================================================
# AI FEATURES MODULE
# ==============================================================================

class AIChatMessage(db.Model):
    """
    Represents conversations occurring within the integrated AI assistant module.
    Maintains history context of student queries and generated system responses.
    """
    __tablename__ = 'ai_chat_messages'
    
    # Primary key identifier for the AI chat message
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student participating in the chat
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Optional foreign key referencing the course context
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    # The role of the message sender (e.g., 'user' or 'model')
    role = db.Column(db.String(20), nullable=False) # 'user' or 'model'
    # The text content of the message
    message = db.Column(db.Text, nullable=False)
    # Timestamp of when the message was sent or generated
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])

class AISummary(db.Model):
    """
    Stores AI-generated summaries of course study materials or long texts.
    Holds text representations and target scopes (e.g., Short, Medium, Detailed).
    """
    __tablename__ = 'ai_summaries'
    
    # Primary key identifier for the AI summary record
    id = db.Column(db.Integer, primary_key=True)
    # Foreign key referencing the student who requested the summary
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Name or identifier of the original file being summarized
    filename = db.Column(db.String(255), nullable=False)
    # The full original text content submitted for summarization
    original_text = db.Column(db.Text, nullable=False)
    # The generated summarized text
    summary_text = db.Column(db.Text, nullable=False)
    # The requested length or style of the summary (e.g., Short, Medium, Detailed)
    summary_type = db.Column(db.String(50), nullable=False) # Short, Medium, Detailed
    # Timestamp of when the summary was created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', foreign_keys=[student_id])