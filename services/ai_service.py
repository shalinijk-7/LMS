import os
import google.generativeai as genai
from flask import current_app
from models import db, AIChatMessage, AISummary, Course, Lesson, StudyMaterial, Quiz, Question, Answer
import json
import PyPDF2
from docx import Document
import google.api_core.exceptions

def get_gemini_model():
    """
    Initializes and returns the Gemini GenerativeModel.
    
    Retrieves the API key from the app configuration, configures the genai client,
    and returns an instance of the 'gemini-flash-lite-latest' model.
    
    Raises:
        ValueError: If the Gemini API key is missing or improperly configured.
    """
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or api_key.strip() == '' or api_key == 'your_gemini_api_key_here':
        raise ValueError("Gemini API key is missing or not configured properly. Please configure GEMINI_API_KEY in your .env file.")
    
    genai.configure(api_key=api_key)
    # Use gemini-flash-lite-latest as it has a separate and higher free tier quota
    return genai.GenerativeModel('gemini-flash-lite-latest')

def format_gemini_error(e):
    """
    Formats Gemini API errors to hide sensitive info and provide clear user-facing messages.
    
    Args:
        e (Exception): The exception caught during Gemini API interaction.
        
    Returns:
        str: A user-friendly error message string.
    """
    if isinstance(e, ValueError):
        return str(e)
    elif isinstance(e, google.api_core.exceptions.InvalidArgument):
        return "Invalid API key or invalid request format provided."
    elif isinstance(e, google.api_core.exceptions.PermissionDenied):
        return "Permission denied. The API key may be invalid or unauthorized."
    elif isinstance(e, google.api_core.exceptions.ResourceExhausted):
        return "API rate limit exceeded. Please try again later."
    elif isinstance(e, google.api_core.exceptions.GoogleAPIError):
        error_msg = str(e)
        if "API key not valid" in error_msg or "API key is invalid" in error_msg or "API_KEY_INVALID" in error_msg:
            return f"Error: The provided Gemini API key is invalid. Please check your .env file."
        return f"Error: An error occurred while communicating with the AI service. Details: {error_msg}"
    else:
        return "An unexpected error occurred while processing your request."

def generate_chat_response(student_id, user_message, course_id=None):
    """
    Generates a chatbot response for the student, maintaining conversational context.
    
    Fetches the last 10 messages from the database to maintain context, sends
    the new message along with system instructions to the Gemini model, and 
    records both the user's message and the AI's response in the database.
    
    Args:
        student_id (int): The ID of the student sending the message.
        user_message (str): The content of the message sent by the user.
        course_id (int, optional): The ID of the course context.
        
    Returns:
        dict: A dictionary containing 'success' status and either the 'reply' 
              or an 'error' message.
    """
    if not user_message or not user_message.strip():
        return {"success": False, "error": "Message cannot be empty."}
        
    # 1. Fetch recent history for context (last 10 messages)
    query = AIChatMessage.query.filter_by(student_id=student_id)
    if course_id:
        query = query.filter_by(course_id=course_id)
    else:
        query = query.filter(AIChatMessage.course_id.is_(None))
        
    history = query.order_by(AIChatMessage.timestamp.desc()).limit(10).all()
    history.reverse() # chronological
    
    # 2. Build history for Gemini
    chat_history = []
    for msg in history:
        chat_history.append({
            "role": msg.role,
            "parts": [msg.message]
        })
    
    # 3. Add system instruction/prompt to guide the AI
    if course_id:
        course = Course.query.get(course_id)
        if course:
            course_context = f"Course Title: {course.title}\nCourse Description: {course.description}\n"
            for lesson in course.lessons:
                course_context += f"Lesson: {lesson.title}\n{lesson.description or ''}\n"
            system_prompt = f"You are an AI assistant for a Learning Management System. The student is asking a question inside the course '{course.title}'. Use the following course content to answer the student's question. If the answer is not available in the course content, clearly tell the student that the information is not covered in the available course material instead of inventing an answer.\n\nCourse Content:\n{course_context}"
        else:
            system_prompt = "You are an AI assistant for a Learning Management System. You help students understand their courses and study topics. Provide clear, simple, accurate, and student-friendly answers. Give step-by-step explanations and examples when needed. Keep answers concise."
    else:
        system_prompt = "You are an AI assistant for a Learning Management System. You help students understand their courses and study topics. Provide clear, simple, accurate, and student-friendly answers. Give step-by-step explanations and examples when needed. Keep answers concise."
    
    try:
        model = get_gemini_model()
        # Initialize a chat session
        chat = model.start_chat(history=chat_history)
        
        # We prepend the system prompt only if there is no history, or we just pass it as a regular message
        if not chat_history:
             prompt = f"{system_prompt}\n\nStudent: {user_message}"
        else:
             prompt = user_message

        response = chat.send_message(prompt)
        ai_reply = response.text
        
        if not ai_reply:
            raise ValueError("The AI generated an empty response.")
        
        # 4. Save messages to DB
        user_msg_db = AIChatMessage(student_id=student_id, course_id=course_id, role='user', message=user_message)
        ai_msg_db = AIChatMessage(student_id=student_id, course_id=course_id, role='model', message=ai_reply)
        db.session.add(user_msg_db)
        db.session.add(ai_msg_db)
        db.session.commit()
        
        return {"success": True, "reply": ai_reply}
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_chat_response: {type(e).__name__} - {e}")
        return {"success": False, "error": format_gemini_error(e)}

def explain_topic(topic_title, description, detail_level='Simple'):
    """
    Generates an AI explanation for a specific study topic.
    
    Constructs a prompt based on the topic title, description, and requested 
    detail level (e.g., Simple vs. Detailed) to generate a customized explanation.
    
    Args:
        topic_title (str): The title or name of the topic to explain.
        description (str): Additional context or description about the topic.
        detail_level (str, optional): The level of detail requested ('Simple' or 'Detailed'). Defaults to 'Simple'.
        
    Returns:
        dict: A dictionary containing 'success' status and the generated 'explanation' 
              or an 'error' message.
    """
    try:
        model = get_gemini_model()
        
        prompt = f"Explain the topic: '{topic_title}'.\n"
        if description:
            prompt += f"Context: {description}\n\n"
            
        if detail_level == 'Simple':
             prompt += "Provide a very simple, easy-to-understand explanation suitable for a beginner. Use simple words and analogies."
        else:
             prompt += "Provide a detailed, in-depth explanation with step-by-step breakdown and examples. Ensure all key points are covered comprehensively."
             
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("The AI generated an empty explanation.")
            
        return {"success": True, "explanation": response.text}
        
    except Exception as e:
        print(f"Error in explain_topic: {type(e).__name__} - {e}")
        return {"success": False, "error": format_gemini_error(e)}

def extract_text_from_file(file_path):
    """
    Extracts and returns the text content from PDF, DOCX, or TXT files.
    
    Includes a file size check to prevent processing excessively large files (>10MB).
    
    Args:
        file_path (str): The absolute or relative path to the file to be processed.
        
    Returns:
        str: The extracted text from the document.
        
    Raises:
        ValueError: If the file size exceeds the limit, the file type is unsupported, 
                    or there is an error reading the file.
    """
    ext = file_path.rsplit('.', 1)[-1].lower()
    text = ""
    
    # Size check (limit to 10MB for processing safety)
    file_size = os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:
        raise ValueError("The uploaded file is too large to process. Please upload a file smaller than 10MB.")
    
    try:
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        elif ext == 'pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        elif ext == 'docx':
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        else:
            raise ValueError(f"Unsupported file type: {ext}")
            
        return text
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError("Failed to extract text from the document. The file might be corrupted or in an unreadable format.")

def summarize_document(student_id, file_path, filename, summary_type):
    """
    Extracts text from a document and generates a summary based on the requested length.
    
    Reads the document, sends a snippet to the AI model with instructions based on 
    the summary_type, and saves the resulting summary to the database.
    
    Args:
        student_id (int): The ID of the student requesting the summary.
        file_path (str): The path to the uploaded document.
        filename (str): The original name of the document.
        summary_type (str): The desired length/detail of the summary ('Short', 'Medium', 'Detailed').
        
    Returns:
        dict: A dictionary containing 'success' status, the 'summary_id', 
              and 'summary_text', or an 'error' message.
    """
    try:
        text = extract_text_from_file(file_path)
        if not text.strip():
             return {"success": False, "error": "Could not extract text from the file or the file is empty."}
             
        model = get_gemini_model()
        
        length_instruction = {
            'Short': 'Provide a brief, high-level overview highlighting only the most critical points. Keep it under 3 paragraphs.',
            'Medium': 'Provide a balanced summary with an overview, important concepts, key definitions, and conclusions.',
            'Detailed': 'Provide an extensive, detailed summary breaking down all major sections, including detailed key points, examples mentioned, and comprehensive conclusions.'
        }
        
        # Limit text to roughly 100k characters to avoid token limit errors
        prompt = f"Summarize the following study material.\n\nInstructions: {length_instruction.get(summary_type, length_instruction['Medium'])}\n\nStudy Material Text:\n{text[:100000]}" 
        
        response = model.generate_content(prompt)
        summary_text = response.text
        
        if not summary_text:
            raise ValueError("The AI generated an empty summary.")
        
        # Save to DB
        summary_record = AISummary(
            student_id=student_id,
            filename=filename,
            original_text=text[:5000], # Save a snippet of original text
            summary_text=summary_text,
            summary_type=summary_type
        )
        db.session.add(summary_record)
        db.session.commit()
        
        return {"success": True, "summary_id": summary_record.id, "summary_text": summary_text}
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in summarize_document: {type(e).__name__} - {e}")
        return {"success": False, "error": format_gemini_error(e)}

def generate_practice_quiz(student_id, course_id, lesson_id, material_id, difficulty, num_questions):
    """
    Generates practice multiple choice questions based on course/lesson content.
    """
    try:
        context_text = ""
        course = Course.query.get(course_id)
        if course:
            context_text += f"Course: {course.title}\n{course.description}\n"
        
        if lesson_id:
            lesson = Lesson.query.get(lesson_id)
            if lesson:
                context_text += f"Lesson: {lesson.title}\n{lesson.description or ''}\n"
                
        if material_id:
            material = StudyMaterial.query.get(material_id)
            if material:
                try:
                    extracted = extract_text_from_file(material.file_path)
                    context_text += f"Study Material Content:\n{extracted[:50000]}\n"
                except Exception as e:
                    print("Could not extract material text:", e)

        if len(context_text.strip()) < 50:
            return {"success": False, "error": "Not enough content available to generate a meaningful quiz."}
            
        model = get_gemini_model()
        prompt = f"""
Generate {num_questions} multiple-choice questions at a '{difficulty}' difficulty level based on the following content. 
Each question must have exactly 4 options. Include the correct answer and a short explanation for each question.
Do not include any information outside of the provided content.

Content:
{context_text}

Output the result strictly in the following JSON format without any markdown wrappers or additional text:
[
  {{
    "question": "Question text here?",
    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
    "correct_option_index": 0,
    "explanation": "Explanation for the correct answer."
  }}
]
"""
        response = model.generate_content(prompt)
        ai_reply = response.text.strip()
        
        if ai_reply.startswith('```json'):
            ai_reply = ai_reply[7:]
        elif ai_reply.startswith('```'):
            ai_reply = ai_reply[3:]
        if ai_reply.endswith('```'):
            ai_reply = ai_reply[:-3]
        ai_reply = ai_reply.strip()
            
        try:
            questions_data = json.loads(ai_reply)
        except json.JSONDecodeError:
            print("Failed to parse JSON:", ai_reply)
            return {"success": False, "error": "AI generated an invalid response format. Please try again."}
            
        if not questions_data or not isinstance(questions_data, list):
             return {"success": False, "error": "AI did not return any valid questions."}
             
        quiz = Quiz(
            course_id=course_id,
            lesson_id=lesson_id if lesson_id else None,
            title=f"AI Practice Quiz - {difficulty}",
            timer_minutes=num_questions * 2,
            is_ai_generated=True,
            student_id=student_id
        )
        db.session.add(quiz)
        db.session.flush() 
        
        for q_data in questions_data:
            question = Question(
                quiz_id=quiz.id,
                text=q_data['question'],
                explanation=q_data.get('explanation', '')
            )
            db.session.add(question)
            db.session.flush()
            
            for idx, opt_text in enumerate(q_data['options']):
                is_correct = (idx == q_data['correct_option_index'])
                answer = Answer(
                    question_id=question.id,
                    text=opt_text,
                    is_correct=is_correct
                )
                db.session.add(answer)
                
        db.session.commit()
        return {"success": True, "quiz_id": quiz.id}
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_practice_quiz: {type(e).__name__} - {e}")
        return {"success": False, "error": format_gemini_error(e)}

