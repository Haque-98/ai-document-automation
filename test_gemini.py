import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Key nahi mili. .env file check karein.")
    raise SystemExit

client = genai.Client(api_key=api_key)

MODEL = "gemini-3.5-flash"

try:
    response = client.models.generate_content(
        model=MODEL,
        contents="Say hello in one short sentence.",
    )
    print("SUCCESS:", response.text)
except Exception as e:
    print("ERROR:", e)