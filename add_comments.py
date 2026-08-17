import os
import glob
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=api_key)

# We will use a fast and capable model
MODEL_NAME = "models/gemini-3.5-flash"
try:
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    print(f"Error initializing model: {e}")
    exit(1)

SYSTEM_PROMPT = """You are an expert software developer. 
Your task is to add clear and meaningful comments throughout the entire provided codebase file.

IMPORTANT STRICT RULES:
1. Do NOT change, remove, rewrite, optimize, or modify ANY existing functionality, logic, HTML, CSS, or variables.
2. Do NOT change variable names, function names, route names, database schemas, API behavior, or business logic.
3. ONLY add comments and documentation.
4. Preserve 100% of the existing functionality exactly as it is.
5. Return ONLY the raw file content. Do NOT wrap your response in markdown code blocks (e.g. ```python). The output will be written directly to the file, so any markdown block will cause syntax errors!
6. Use simple and professional comments that explain the action being performed. Do not add comments for every single obvious line. Focus on important logic and sections.

File Content to comment:
"""

DIRECTORIES_TO_SCAN = [
    "models/**/*.py",
    "routes/**/*.py",
    "services/**/*.py",
    "utils/**/*.py",
    "app.py",
    "config.py",
    "seed_courses.py",
    "static/js/**/*.js",
    "static/css/**/*.css",
    "templates/**/*.html"
]

def clean_output(text):
    # Remove markdown code blocks if the model accidentally included them
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines.pop(0)
    if lines and lines[-1].startswith("```"):
        lines.pop()
    return "\n".join(lines)

def process_file(filepath):
    print(f"Processing: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            print("  Skipping empty file.")
            return

        response = model.generate_content(SYSTEM_PROMPT + content)
        new_content = clean_output(response.text)

        # Write back to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("  Success!")
        time.sleep(1) # Simple rate limiting
    except Exception as e:
        print(f"  Error processing {filepath}: {e}")

def main():
    files_to_process = []
    for pattern in DIRECTORIES_TO_SCAN:
        if "*" in pattern:
            files_to_process.extend(glob.glob(pattern, recursive=True))
        else:
            if os.path.exists(pattern):
                files_to_process.append(pattern)

    # Filter out pycache or binaries if any accidentally matched
    files_to_process = [f for f in files_to_process if "__pycache__" not in f]

    print(f"Found {len(files_to_process)} files to process.")
    
    for filepath in files_to_process:
        process_file(filepath)

    print("All files processed.")

if __name__ == "__main__":
    main()
