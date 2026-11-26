import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.5-flash"

invoice_text = """
ABC Traders Pvt Ltd
INVOICE #INV-2026-045
Date: 12 November 2026
Due Date: 27 November 2026
Bill To: Ali Hassan

Item: Office Chairs x 4 ... 80,000
Subtotal: 80,000
Sales Tax (17%): 13,600
Total: PKR 93,600
"""

prompt = f"""
You are an invoice data extraction assistant.
Read the invoice text below and return ONLY a JSON object with these keys:
vendor_name, invoice_number, invoice_date, due_date, customer_name,
subtotal, tax_amount, total_amount, currency.
Rules:
- Dates must be in YYYY-MM-DD format.
- Numbers must be plain numbers without commas.
- If a value is missing, use null. Never guess.

Invoice text:
{invoice_text}
"""

response = client.models.generate_content(
    model=MODEL,
    contents=prompt,
    config=types.GenerateContentConfig(response_mime_type="application/json"),
)

print("Raw text from AI:")
print(response.text)

data = json.loads(response.text)
print("\nTotal amount is:", data["total_amount"])