from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from utils.decorators import student_required
from models import db, AIChatMessage, AISummary, Course, Enrollment, Lesson, StudyMaterial
from services.ai_service import generate_chat_response, explain_topic, summarize_document, generate_practice_quiz
from werkzeug.utils import secure_filename
import os

# Initialize Flask Blueprint for AI-related operations and interfaces
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

# ==========================================
# 1. AI Chatbot Section
# ==========================================

@ai_bp.route('/chat', methods=['GET'])
@login_required
@student_required
def chat():
    """
    Route to render the AI chatbot interface for students.
    Fetches the student's chat history to display in the UI.
    """
    course_id = request.args.get('course_id', type=int)
    
    # Retrieve chronologically ordered chat messages associated with the current student
    query = AIChatMessage.query.filter_by(student_id=current_user.id)
    if course_id:
        query = query.filter_by(course_id=course_id)
    else:
        query = query.filter(AIChatMessage.course_id.is_(None))
        
    history = query.order_by(AIChatMessage.timestamp.asc()).all()
    
    course = None
    if course_id:
        course = Course.query.get(course_id)
        
    return render_template('ai/chat.html', history=history, course=course)

@ai_bp.route('/api/chat', methods=['POST'])
@login_required
@student_required
def api_chat():
    """
    API endpoint to handle incoming chat messages from the student.
    Delegates the processing to the AI service and returns the generated response.
    """
    # Retrieve JSON payload from the request
    data = request.get_json()
    message = data.get('message')
    course_id = data.get('course_id')
    
    # Check that message content is provided
    if not message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400
        
    # Delegate the processing and message generation to the AI integration service
    result = generate_chat_response(current_user.id, message, course_id=course_id)
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


# ==========================================
# 2. AI Explanation Section
# ==========================================

@ai_bp.route('/api/explain', methods=['POST'])
@login_required
@student_required
def api_explain():
    """
    API endpoint to request an AI explanation of a difficult topic.
    Passes the topic title, description, and desired detail level to the AI service.
    """
    # Extract the topic metadata and configuration settings from the request body
    data = request.get_json()
    topic_title = data.get('topic_title')
    description = data.get('description', '')
    detail_level = data.get('detail_level', 'Simple') # Defaults to 'Simple' if not specified
    
    # Ensure the core topic is present
    if not topic_title:
        return jsonify({"success": False, "error": "Topic title is required."}), 400
        
    # Execute the explanation generation algorithm via the AI service
    result = explain_topic(topic_title, description, detail_level)
    if result.get('success'):
        return jsonify(result)
    else:
        return jsonify(result), 500


# ==========================================
# 3. AI Practice Questions Section
# ==========================================

@ai_bp.route('/practice', methods=['GET'])
@login_required
@student_required
def practice_form():
    """
    Route to render the AI practice quiz generator interface.
    """
    # Fetch courses the student is enrolled in
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    courses = [e.course for e in enrollments]
    
    from models import Quiz
    past_quizzes = Quiz.query.filter_by(student_id=current_user.id, is_ai_generated=True).order_by(Quiz.id.desc()).all()
    
    return render_template('ai/practice_form.html', courses=courses, past_quizzes=past_quizzes)

@ai_bp.route('/api/course_content/<int:course_id>', methods=['GET'])
@login_required
@student_required
def course_content(course_id):
    """API endpoint to get lessons and materials for a given course."""
    course = Course.query.get_or_404(course_id)
    lessons_data = []
    for lesson in course.lessons:
        materials_data = [{"id": m.id, "title": m.title} for m in lesson.materials]
        lessons_data.append({
            "id": lesson.id,
            "title": lesson.title,
            "materials": materials_data
        })
    return jsonify({"success": True, "lessons": lessons_data})

@ai_bp.route('/api/practice/generate', methods=['POST'])
@login_required
@student_required
def api_practice_generate():
    """
    API endpoint to generate AI practice questions.
    """
    data = request.get_json()
    course_id = data.get('course_id')
    lesson_id = data.get('lesson_id')
    material_id = data.get('material_id')
    difficulty = data.get('difficulty', 'Medium')
    num_questions = data.get('num_questions', 3)
    
    if not course_id:
         return jsonify({"success": False, "error": "Course ID is required."}), 400
         
    try:
        num_questions = int(num_questions)
        if num_questions < 1 or num_questions > 10:
             return jsonify({"success": False, "error": "Number of questions must be between 1 and 10."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid number of questions."}), 400
        
    result = generate_practice_quiz(
        student_id=current_user.id,
        course_id=course_id,
        lesson_id=lesson_id,
        material_id=material_id,
        difficulty=difficulty,
        num_questions=num_questions
    )
    
    if result.get('success'):
        from flask import url_for
        result['redirect_url'] = url_for('quiz.take_quiz', quiz_id=result['quiz_id'])
        return jsonify(result)
    else:
        return jsonify(result), 500

# ==========================================
# 4. AI Summarizer Section
# ==========================================

@ai_bp.route('/summary', methods=['GET', 'POST'])
@login_required
@student_required
def summary():
    """
    Route to render the AI summarizer dashboard and handle document uploads.
    Accepts document uploads via POST, validates file types, saves the file, 
    and generates a summary using the AI service.
    """
    if request.method == 'POST':
        # Validate that the file field exists in the multipart/form-data payload
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file uploaded."}), 400
            
        file = request.files['file']
        summary_type = request.form.get('summary_type', 'Medium')
        
        # Validate that a file has been selected
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected."}), 400
            
        # Validate the file extension to ensure it is one of the supported document formats
        allowed_extensions = {'pdf', 'docx', 'txt'}
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in allowed_extensions:
            return jsonify({"success": False, "error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400
            
        # Sanitize filename and save the uploaded document to the designated upload directory
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Delegate document parsing and summary generation to the AI summarizer service
        result = summarize_document(current_user.id, file_path, filename, summary_type)
        
        # Optional: delete the file after summarizing to save space, or keep it if needed.
        # We will keep it for now in case they want to download it again.
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500

    # GET request processing: Retrieve all existing summaries for the current student
    summaries = AISummary.query.filter_by(student_id=current_user.id).order_by(AISummary.created_at.desc()).all()
    return render_template('ai/summary.html', summaries=summaries)

@ai_bp.route('/summary/<int:summary_id>', methods=['GET'])
@login_required
@student_required
def get_summary(summary_id):
    """
    Route to fetch and view a previously generated document summary.
    Ensures that students can only access their own summaries.
    """
    # Retrieve the requested summary only if it belongs to the logged-in student, otherwise return 404
    summary_record = AISummary.query.filter_by(id=summary_id, student_id=current_user.id).first_or_404()
    return render_template('ai/summary_view.html', summary=summary_record)