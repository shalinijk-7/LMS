import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    response = model.generate_content("Hello")
    print("Success:", response.text)
except Exception as e:
    print("Error:", e)
