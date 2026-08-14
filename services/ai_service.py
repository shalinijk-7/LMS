import os
import google.generativeai as genai
from flask import current_app
from models import db, AIChatMessage, AISummary
import PyPDF2
from docx import Document
import google.api_core.exceptions

def get_gemini_model():
    """Initializes and returns the Gemini model."""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or api_key.strip() == '' or api_key == 'your_gemini_api_key_here':
        raise ValueError("Gemini API key is missing or not configured properly. Please configure GEMINI_API_KEY in your .env file.")
    
    genai.configure(api_key=api_key)
    # Use gemini-flash-lite-latest as it has a separate and higher free tier quota
    return genai.GenerativeModel('gemini-flash-lite-latest')

def format_gemini_error(e):
    """Formats Gemini API errors to hide sensitive info and provide clear messages."""
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

def generate_chat_response(student_id, user_message):
    """
    Generates a chatbot response for the student, maintaining context.
    """
    if not user_message or not user_message.strip():
        return {"success": False, "error": "Message cannot be empty."}
        
    # 1. Fetch recent history for context (last 10 messages)
    history = AIChatMessage.query.filter_by(student_id=student_id).order_by(AIChatMessage.timestamp.desc()).limit(10).all()
    history.reverse() # chronological
    
    # 2. Build history for Gemini
    chat_history = []
    for msg in history:
        chat_history.append({
            "role": msg.role,
            "parts": [msg.message]
        })
    
    # 3. Add system instruction/prompt to guide the AI
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
        user_msg_db = AIChatMessage(student_id=student_id, role='user', message=user_message)
        ai_msg_db = AIChatMessage(student_id=student_id, role='model', message=ai_reply)
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
    Generates an explanation for a difficult lesson or topic.
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
    Extracts text from PDF, DOCX, or TXT files.
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
    Extracts text and generates a summary based on the requested length.
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
