from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import db, AIChatMessage, AISummary, Course
from services.ai_service import generate_chat_response, explain_topic, summarize_document
from werkzeug.utils import secure_filename
import os

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

# ==========================================
# 1. AI Chatbot
# ==========================================
@ai_bp.route('/chat', methods=['GET'])
@login_required
@student_required
def chat():
    """Renders the AI chatbot interface for students."""
    # Get recent history
    history = AIChatMessage.query.filter_by(student_id=current_user.id).order_by(AIChatMessage.timestamp.asc()).all()
    return render_template('ai/chat.html', history=history)

@ai_bp.route('/api/chat', methods=['POST'])
@login_required
@student_required
def api_chat():
    """Handles incoming chat messages from the student."""
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400
        
    result = generate_chat_response(current_user.id, message)
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


# ==========================================
# 2. AI Explanation
# ==========================================
@ai_bp.route('/api/explain', methods=['POST'])
@login_required
@student_required
def api_explain():
    """Handles requests for explaining a difficult topic."""
    data = request.get_json()
    topic_title = data.get('topic_title')
    description = data.get('description', '')
    detail_level = data.get('detail_level', 'Simple') # 'Simple' or 'Detailed'
    
    if not topic_title:
        return jsonify({"success": False, "error": "Topic title is required."}), 400
        
    result = explain_topic(topic_title, description, detail_level)
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


# ==========================================
# 3. AI Summarizer
# ==========================================
@ai_bp.route('/summary', methods=['GET', 'POST'])
@login_required
@student_required
def summary():
    """Renders the summary dashboard and handles file uploads."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded."}), 400
            
        file = request.files['file']
        summary_type = request.form.get('summary_type', 'Medium')
        
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected."}), 400
            
        # Validate extension
        allowed_extensions = {'pdf', 'docx', 'txt'}
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in allowed_extensions:
            return jsonify({"success": False, "error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400
            
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process and Summarize
        result = summarize_document(current_user.id, file_path, filename, summary_type)
        
        # Optional: delete the file after summarizing to save space, or keep it if needed.
        # We will keep it for now in case they want to download it again.
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500

    # GET request
    # Fetch user's saved summaries
    summaries = AISummary.query.filter_by(student_id=current_user.id).order_by(AISummary.created_at.desc()).all()
    return render_template('ai/summary.html', summaries=summaries)

@ai_bp.route('/summary/<int:summary_id>', methods=['GET'])
@login_required
@student_required
def get_summary(summary_id):
    """Fetches a specific saved summary for viewing."""
    summary_record = AISummary.query.filter_by(id=summary_id, student_id=current_user.id).first_or_404()
    return render_template('ai/summary_view.html', summary=summary_record)
