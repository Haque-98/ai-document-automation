import os
import json
import time
import streamlit as st
import pytesseract
from PIL import Image
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\buth\AppData\Local\Tesseract-OCR\tesseract.exe"


def extract_invoice_data(text):
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
{text}
"""
    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            return json.loads(response.text)
        except Exception as e:
            last_error = e
            time.sleep(2 * (attempt + 1))
    raise last_error


st.title("AI Document Automation")
st.write("Welcome to my AI Document Automation System")

uploaded_file = st.file_uploader("Upload an invoice", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.success("File uploaded: " + uploaded_file.name)

    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages[:3]:
            text = text + page.extract_text() + "\n"
    else:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded image")
        text = pytesseract.image_to_string(image)

    st.subheader("Extracted text")
    st.text(text)

    if st.button("Extract with AI"):
        if not text.strip():
            st.error("No text found in this document.")
        else:
            try:
                data = extract_invoice_data(text)
                st.subheader("Structured data (JSON)")
                st.json(data)
            except Exception as e:
                st.error("AI extraction failed: " + str(e))