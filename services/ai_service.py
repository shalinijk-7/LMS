import os
from flask import current_app
from models import db, AIChatMessage, AISummary
import PyPDF2
from docx import Document

try:
    from google import genai
except ImportError:
    genai = None


def get_client():
    """Create Gemini client with API key from config."""
    if genai is None:
        raise ValueError(
            "Package 'google-genai' is not installed. Run: pip install -U google-genai"
        )

    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or not str(api_key).strip():
        raise ValueError(
            "GEMINI_API_KEY is missing. Add it to your .env file."
        )

    return genai.Client(api_key=api_key.strip())


# Models that work with new (AQ.) keys — tried in order
MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-1.5-flash",
]


def generate_text(prompt: str) -> str:
    """Generate text using the first working model."""
    client = get_client()
    last_error = None

    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            text = getattr(response, "text", None)
            if text:
                return text.strip()
            # some SDK versions put text elsewhere
            if hasattr(response, "candidates") and response.candidates:
                parts = response.candidates[0].content.parts
                if parts:
                    return parts[0].text.strip()
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(
        f"No working Gemini model found. Last error: {last_error}. "
        "Try updating google-genai: pip install -U google-genai"
    )


def format_error(e):
    msg = str(e)
    if "API key" in msg or "API_KEY" in msg or "401" in msg or "UNAUTHENTICATED" in msg:
        return "Invalid or unauthorized API key. Check GEMINI_API_KEY in .env."
    if "404" in msg or "not found" in msg.lower() or "NOT_FOUND" in msg:
        return "AI model not found. Update models in ai_service.py or run: pip install -U google-genai"
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
        return "API rate limit / quota exceeded. Try again later."
    return f"AI error: {msg}"


def generate_chat_response(student_id, user_message):
    if not user_message or not user_message.strip():
        return {"success": False, "error": "Message cannot be empty."}

    history = (
        AIChatMessage.query.filter_by(student_id=student_id)
        .order_by(AIChatMessage.timestamp.desc())
        .limit(10)
        .all()
    )
    history.reverse()

    history_text = ""
    for msg in history:
        role = "Student" if msg.role == "user" else "Assistant"
        history_text += f"{role}: {msg.message}\n"

    prompt = (
        "You are AuraLearn AI Tutor, a helpful educational assistant for students.\n"
        "Answer clearly and helpfully.\n\n"
        f"Previous conversation:\n{history_text}\n"
        f"Student: {user_message}\n"
        "Assistant:"
    )

    try:
        bot_reply = generate_text(prompt)

        db.session.add(AIChatMessage(student_id=student_id, role="user", message=user_message))
        db.session.add(AIChatMessage(student_id=student_id, role="assistant", message=bot_reply))
        db.session.commit()

        return {"success": True, "reply": bot_reply}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": format_error(e)}


def explain_topic(topic_title, description="", detail_level="medium"):
    if not topic_title or not topic_title.strip():
        return {"success": False, "error": "Topic title is required."}

    level_instruction = {
        "short": "Give a brief explanation in 3-5 sentences.",
        "medium": "Give a clear explanation with key points and one example.",
        "detailed": "Give a detailed explanation with examples and takeaways.",
    }.get(detail_level, "Give a clear explanation with key points.")

    prompt = (
        f"You are an expert tutor.\n"
        f"Topic: {topic_title}\n"
        f"Extra context: {description or 'None'}\n"
        f"Instruction: {level_instruction}\n"
        "Use simple language."
    )

    try:
        explanation = generate_text(prompt)
        return {"success": True, "explanation": explanation}
    except Exception as e:
        return {"success": False, "error": format_error(e)}


def extract_text_from_file(file_path):
    ext = file_path.rsplit(".", 1)[-1].lower()
    text = ""
    try:
        if ext == "pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        elif ext == "docx":
            doc = Document(file_path)
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif ext == "txt":
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            return None
    except Exception:
        return None
    return text.strip() if text and text.strip() else None


def summarize_document(student_id, file_path, filename, summary_type="Medium"):
    text = extract_text_from_file(file_path)
    if not text:
        return {
            "success": False,
            "error": "Could not extract text from the file. Use a valid PDF, DOCX, or TXT.",
        }

    max_chars = 25000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Content truncated...]"

    type_instruction = {
        "Short": "Write a short summary in 5-8 bullet points.",
        "Medium": "Write a clear medium-length summary with main ideas.",
        "Detailed": "Write a detailed summary of all important sections.",
    }.get(summary_type, "Write a clear medium-length summary.")

    prompt = (
        "You are an academic assistant. Summarize this document for a student.\n"
        f"Style: {type_instruction}\n\n"
        f"Document:\n{text}"
    )

    try:
        summary_text = generate_text(prompt)
        record = AISummary(
            student_id=student_id,
            filename=filename,
            original_text=text[:5000],
            summary_type=summary_type,
            summary_text=summary_text,
        )
        db.session.add(record)
        db.session.commit()
        return {"success": True, "summary": summary_text, "summary_id": record.id}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": format_error(e)}