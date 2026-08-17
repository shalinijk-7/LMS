from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Message, Course, User, db
from sqlalchemy import or_, and_

# Initialize the Blueprint for chat operations
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/')
@login_required
def chat_interface():
    """
    Renders the main chat application interface with loaded contact lists and 
    course group chats depending on the current user's role.
    """
    # Identify available chats based on user role (Student or Instructor)
    if current_user.role.name == 'student':
        # Students see their enrolled courses and the respective instructors
        courses = [e.course for e in current_user.enrollments] # Assuming Enrollment model maps to user.enrollments
        instructor_ids = [c.instructor_id for c in courses if c]
        users_to_chat = User.query.filter(User.id.in_(instructor_ids)).all() if instructor_ids else []
    elif current_user.role.name == 'instructor':
        # Instructors see courses they teach and all students enrolled in them
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        student_ids = []
        for course in courses:
            for enrollment in course.enrollments:
                student_ids.append(enrollment.user_id)
        users_to_chat = User.query.filter(User.id.in_(list(set(student_ids)))).all() if student_ids else []
    else:
        courses = []
        users_to_chat = []

    # Calculate unread message counts for both direct messages and course channels
    unread_counts = {}
    course_unread_counts = {}
    if current_user.is_authenticated:
        from models import CourseChatReadStatus
        # Retrieve all unread private messages directed to the current user
        unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).all()
        for msg in unread_msgs:
            unread_counts[msg.sender_id] = unread_counts.get(msg.sender_id, 0) + 1
            
        # Determine unread counts for course channels based on the user's last read message ID
        for course in courses:
            status = CourseChatReadStatus.query.filter_by(user_id=current_user.id, course_id=course.id).first()
            last_id = status.last_read_message_id if status else 0
            count = Message.query.filter_by(course_id=course.id).filter(Message.id > last_id).count()
            if count > 0:
                course_unread_counts[course.id] = count

    return render_template('chat/chat.html', courses=courses, users=users_to_chat, unread_counts=unread_counts, course_unread_counts=course_unread_counts)

@chat_bp.route('/history/<chat_type>/<int:chat_id>')
@login_required
def get_chat_history(chat_type, chat_id):
    """
    Retrieves the chronological list of messages for a specific course channel or direct user-to-user chat,
    and automatically marks retrieved messages as read.
    """
    if chat_type == 'course':
        # Fetch group messages related to the course
        messages = Message.query.filter_by(course_id=chat_id).order_by(Message.timestamp.asc()).all()
        
        # Keep track of the last read message in the course for the current user
        if messages:
            last_msg_id = messages[-1].id
            from models import CourseChatReadStatus
            status = CourseChatReadStatus.query.filter_by(user_id=current_user.id, course_id=chat_id).first()
            if not status:
                status = CourseChatReadStatus(user_id=current_user.id, course_id=chat_id, last_read_message_id=last_msg_id)
                db.session.add(status)
            else:
                status.last_read_message_id = max(status.last_read_message_id, last_msg_id)
            db.session.commit()
    elif chat_type == 'user':
        # Fetch direct messages between the current user and target user (bidirectional)
        messages = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == chat_id),
                and_(Message.sender_id == chat_id, Message.receiver_id == current_user.id)
            )
        ).order_by(Message.timestamp.asc()).all()
        
        # Mark incoming direct messages as read
        unread_msgs = [m for m in messages if m.receiver_id == current_user.id and not m.is_read]
        if unread_msgs:
            for m in unread_msgs:
                m.is_read = True
            db.session.commit()
    else:
        return jsonify({'error': 'Invalid chat type'}), 400

    # Serialize message objects with all relevant metadata into JSON format
    results = []
    for msg in messages:
        sender_user = User.query.get(msg.sender_id)
        results.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': sender_user.name if sender_user else 'Unknown',
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'file_url': msg.file_url,
            'is_edited': msg.is_edited,
            'is_deleted': msg.is_deleted,
            'is_pinned': msg.is_pinned,
            'is_announcement': msg.is_announcement,
            'reply_to_id': msg.reply_to_id,
            'message_type': msg.message_type,
            'reactions': [{'emoji': r.emoji, 'user_id': r.user_id} for r in getattr(msg, 'reactions', [])]
        })
    return jsonify(results)

import os
from werkzeug.utils import secure_filename

@chat_bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """
    Processes file uploads for chat attachments, ensuring secure filenames and directory persistence.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Prefix filename with user ID to prevent naming collisions, then secure the path
    filename = secure_filename(f"{current_user.id}_{file.filename}")
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    file_url = f"/static/uploads/{filename}"
    return jsonify({'file_url': file_url})

@chat_bp.route('/info/<chat_type>/<int:chat_id>')
@login_required
def get_chat_info(chat_type, chat_id):
    """
    Fetches details and metadata about a course or user to display in the chat context panel.
    """
    if chat_type == 'course':
        course = Course.query.get_or_404(chat_id)
        total_students = len(course.enrollments)
        return jsonify({
            'title': course.title,
            'instructor': course.instructor.name,
            'total_students': total_students,
            'description': getattr(course, 'description', '')
        })
    elif chat_type == 'user':
        user = User.query.get_or_404(chat_id)
        return jsonify({
            'name': user.name,
            'role': user.role.name.capitalize(),
            'email': user.email
        })
    return jsonify({'error': 'Invalid chat type'}), 400