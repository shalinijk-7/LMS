from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import Message, Course, User, db
from sqlalchemy import or_, and_

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/')
@login_required
def chat_interface():
    # Get courses the user is part of (for group chats)
    if current_user.role.name == 'student':
        courses = [e.course for e in current_user.enrollments] # Assuming Enrollment model maps to user.enrollments
        instructor_ids = [c.instructor_id for c in courses if c]
        users_to_chat = User.query.filter(User.id.in_(instructor_ids)).all() if instructor_ids else []
    elif current_user.role.name == 'instructor':
        courses = Course.query.filter_by(instructor_id=current_user.id).all()
        student_ids = []
        for course in courses:
            for enrollment in course.enrollments:
                student_ids.append(enrollment.user_id)
        users_to_chat = User.query.filter(User.id.in_(list(set(student_ids)))).all() if student_ids else []
    else:
        courses = []
        users_to_chat = []

    unread_counts = {}
    course_unread_counts = {}
    if current_user.is_authenticated:
        from models import CourseChatReadStatus
        unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).all()
        for msg in unread_msgs:
            unread_counts[msg.sender_id] = unread_counts.get(msg.sender_id, 0) + 1
            
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
    if chat_type == 'course':
        messages = Message.query.filter_by(course_id=chat_id).order_by(Message.timestamp.asc()).all()
        
        # Mark course messages as read
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
        messages = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == chat_id),
                and_(Message.sender_id == chat_id, Message.receiver_id == current_user.id)
            )
        ).order_by(Message.timestamp.asc()).all()
        
        # Mark incoming messages as read
        unread_msgs = [m for m in messages if m.receiver_id == current_user.id and not m.is_read]
        if unread_msgs:
            for m in unread_msgs:
                m.is_read = True
            db.session.commit()
    else:
        return jsonify({'error': 'Invalid chat type'}), 400

    results = []
    for msg in messages:
        sender_user = User.query.get(msg.sender_id)
        results.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': sender_user.name if sender_user else 'Unknown',
            'content': msg.content,
            'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'file_url': msg.file_url
        })
    return jsonify(results)
