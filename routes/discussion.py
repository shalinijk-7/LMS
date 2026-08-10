# Handles discussion forums and course conversations.
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import DiscussionThread, DiscussionReply
from models import Course
from models import db

discussion_bp = Blueprint('discussion', __name__, url_prefix='/discussion')

@discussion_bp.route('/course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def list_discussions(course_id):
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        new_discussion = DiscussionThread(title=title, content=content, course_id=course.id, user_id=current_user.id)
        db.session.add(new_discussion)
        db.session.commit()
        flash('Discussion created successfully!', 'success')
        return redirect(url_for('discussion.list_discussions', course_id=course.id))
        
    discussions = DiscussionThread.query.filter_by(course_id=course.id).order_by(DiscussionThread.created_at.desc()).all()
    return render_template('discussions/discussion_list.html', course=course, discussions=discussions)

@discussion_bp.route('/view/<int:discussion_id>', methods=['GET', 'POST'])
@login_required
def view_discussion(discussion_id):
    discussion = DiscussionThread.query.get_or_404(discussion_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        new_reply = DiscussionReply(content=content, thread_id=discussion.id, user_id=current_user.id)
        db.session.add(new_reply)
        db.session.commit()
        flash('Reply posted!', 'success')
        return redirect(url_for('discussion.view_discussion', discussion_id=discussion.id))
        
    return render_template('discussions/view_discussion.html', discussion=discussion)
