import io
import os
import json
import time
import sqlite3
from datetime import date, datetime

import pandas as pd
import streamlit as st
import pytesseract
from PIL import Image
from pypdf import PdfReader
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ============================================================
# 1. SETTINGS
# ============================================================
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH",
    r"C:\Users\buth\AppData\Local\Tesseract-OCR\tesseract.exe",
)
DB_FILE = "invoices.db"
MAX_PDF_PAGES = 3
ALLOWED_CURRENCIES = ["PKR", "USD", "EUR", "GBP", "AED", "SAR"]

TEXT_FIELDS = [
    "vendor_name", "invoice_number", "invoice_date", "due_date",
    "customer_name", "currency",
]
NUMBER_FIELDS = ["subtotal", "tax_amount", "total_amount"]
ALL_FIELDS = [
    "vendor_name", "invoice_number", "invoice_date", "due_date",
    "customer_name", "subtotal", "tax_amount", "total_amount", "currency",
]

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ============================================================
# 2. TEXT EXTRACTION (PDF + OCR)
# ============================================================
def read_document_text(uploaded_file):
    """Return (text, image_or_None). Raises ValueError with a friendly message."""
    if uploaded_file.type == "application/pdf":
        try:
            reader = PdfReader(uploaded_file)
        except Exception:
            raise ValueError("This PDF could not be opened. It may be corrupted or password protected.")
        text = ""
        for page in reader.pages[:MAX_PDF_PAGES]:
            text += (page.extract_text() or "") + "\n"
        if not text.strip():
            raise ValueError(
                "No text found in this PDF. It may be a scanned PDF. "
                "Please upload it as a JPG or PNG image instead."
            )
        return text, None

    try:
        image = Image.open(uploaded_file)
        image.load()
    except Exception:
        raise ValueError("This image could not be opened. Please upload a valid JPG or PNG.")
    try:
        text = pytesseract.image_to_string(image)
    except Exception as e:
        raise ValueError("OCR failed. Check the Tesseract path in your settings. (" + str(e) + ")")
    if not text.strip():
        raise ValueError("No text could be read from this image. Try a clearer picture.")
    return text, image


# ============================================================
# 3. AI EXTRACTION
# ============================================================
def extract_invoice_data(text):
    """Send text to Gemini, get a dict back. Retries on temporary errors."""
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

    client = genai.Client(api_key=API_KEY)
    prompt = f"""
You are an invoice data extraction assistant.
Read the invoice text below and return ONLY a JSON object with these keys:
vendor_name, invoice_number, invoice_date, due_date, customer_name,
subtotal, tax_amount, total_amount, currency.
Rules:
- Dates must be in YYYY-MM-DD format.
- Numbers must be plain numbers without commas or currency symbols.
- Currency must be a 3-letter code such as PKR, USD, EUR.
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
            data = json.loads(response.text)
            if not isinstance(data, dict):
                raise ValueError("AI returned an unexpected format.")
            return data
        except Exception as e:
            last_error = e
            time.sleep(2 * (attempt + 1))
    raise last_error


# ============================================================
# 4. CLEANING + VALIDATION
# ============================================================
def parse_number(value):
    """Turn '93,600' or 93600 or '' into a float or None."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).replace(",", "").strip()
    if cleaned == "":
        return None
    return float(cleaned)  # may raise ValueError


def clean_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value != "" else None


def validate_invoice(data, existing_numbers=None):
    """Return a list of problems found in the invoice data."""
    issues = []

    for field in ALL_FIELDS:
        if data.get(field) is None:
            issues.append("Missing field: " + field)

    subtotal = data.get("subtotal")
    tax = data.get("tax_amount")
    total = data.get("total_amount")
    if None not in (subtotal, tax, total):
        if abs((subtotal + tax) - total) > 0.01:
            issues.append(
                "Amount mismatch: subtotal + tax = "
                + str(round(subtotal + tax, 2))
                + " but total is "
                + str(total)
            )

    for field in NUMBER_FIELDS:
        value = data.get(field)
        if value is not None and value < 0:
            issues.append("Negative amount in: " + field)

    parsed_dates = {}
    for field in ["invoice_date", "due_date"]:
        value = data.get(field)
        if value is not None:
            try:
                parsed_dates[field] = date.fromisoformat(value)
            except ValueError:
                issues.append("Invalid date format in " + field + " (use YYYY-MM-DD)")
    if "invoice_date" in parsed_dates and "due_date" in parsed_dates:
        if parsed_dates["due_date"] < parsed_dates["invoice_date"]:
            issues.append("Due date is before invoice date")

    currency = data.get("currency")
    if currency is not None and currency.upper() not in ALLOWED_CURRENCIES:
        issues.append("Unusual currency: " + str(currency))

    number = data.get("invoice_number")
    if number is not None and existing_numbers and number in existing_numbers:
        issues.append("Possible duplicate: invoice number " + number + " is already in history")

    return issues


# ============================================================
# 5. DATABASE (SQLite)
# ============================================================
def get_connection():
    return sqlite3.connect(DB_FILE)


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                file_name TEXT,
                vendor_name TEXT,
                invoice_number TEXT,
                invoice_date TEXT,
                due_date TEXT,
                customer_name TEXT,
                subtotal REAL,
                tax_amount REAL,
                total_amount REAL,
                currency TEXT,
                status TEXT,
                issues TEXT
            )
            """
        )


def save_invoice(file_name, data, issues):
    status = "Needs review" if issues else "OK"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO invoices (
                created_at, file_name, vendor_name, invoice_number, invoice_date,
                due_date, customer_name, subtotal, tax_amount, total_amount,
                currency, status, issues
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                file_name,
                data.get("vendor_name"),
                data.get("invoice_number"),
                data.get("invoice_date"),
                data.get("due_date"),
                data.get("customer_name"),
                data.get("subtotal"),
                data.get("tax_amount"),
                data.get("total_amount"),
                data.get("currency"),
                status,
                "; ".join(issues),
            ),
        )
    return status


def load_history():
    with get_connection() as conn:
        return pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", conn)


def existing_invoice_numbers():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT invoice_number FROM invoices WHERE invoice_number IS NOT NULL"
        ).fetchall()
    return {row[0] for row in rows}


def delete_invoice(invoice_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM invoices WHERE id = ?", (int(invoice_id),))


# ============================================================
# 6. EXPORT
# ============================================================
def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Invoices")
    return buffer.getvalue()


# ===== UI =====
# ============================================================
# 7. USER INTERFACE
# ============================================================
st.set_page_config(page_title="AI Document Automation", page_icon="🧾", layout="wide")
init_db()

st.title("🧾 AI Document Automation")
st.caption("Upload an invoice, let AI read it, review the result, and save it to your history.")

tab_process, tab_history = st.tabs(["📤 Process Invoice", "📚 History & Export"])

# ---------------- TAB 1: PROCESS ----------------
with tab_process:
    uploaded_file = st.file_uploader(
        "Upload an invoice (PDF, JPG, PNG)", type=["pdf", "jpg", "jpeg", "png"]
    )

    if uploaded_file is not None:
        file_id = uploaded_file.name + "-" + str(uploaded_file.size)

        try:
            text, image = read_document_text(uploaded_file)
        except ValueError as e:
            st.error(str(e))
            st.stop()

        left, right = st.columns(2)
        with left:
            st.subheader("Document")
            if image is not None:
                st.image(image, caption=uploaded_file.name)
            else:
                st.success("PDF read: " + uploaded_file.name)
            with st.expander("Show extracted text"):
                st.text(text)

        with right:
            st.subheader("AI Extraction")
            if st.button("Extract with AI", type="primary"):
                with st.spinner("AI is reading the invoice..."):
                    try:
                        data = extract_invoice_data(text)
                        st.session_state["extracted"] = data
                        st.session_state["extracted_file"] = file_id
                        st.session_state["extraction_count"] = (
                            st.session_state.get("extraction_count", 0) + 1
                        )
                    except Exception as e:
                        st.error("AI extraction failed: " + str(e))

            has_result = (
                "extracted" in st.session_state
                and st.session_state.get("extracted_file") == file_id
            )

            if has_result:
                data = st.session_state["extracted"]
                run_id = st.session_state["extraction_count"]

                st.write("Review and correct the values below, then save.")
                with st.form("review_form"):
                    edited = {}
                    for field in TEXT_FIELDS:
                        label = field.replace("_", " ").title()
                        edited[field] = st.text_input(
                            label,
                            value="" if data.get(field) is None else str(data.get(field)),
                            key=field + "_" + str(run_id),
                        )
                    for field in NUMBER_FIELDS:
                        label = field.replace("_", " ").title()
                        edited[field] = st.text_input(
                            label,
                            value="" if data.get(field) is None else str(data.get(field)),
                            key=field + "_" + str(run_id),
                        )
                    submitted = st.form_submit_button("Validate and Save")

                if submitted:
                    final = {}
                    number_error = False
                    for field in TEXT_FIELDS:
                        final[field] = clean_text(edited[field])
                    for field in NUMBER_FIELDS:
                        try:
                            final[field] = parse_number(edited[field])
                        except ValueError:
                            st.error("'" + field + "' must be a number.")
                            number_error = True
                    if final.get("currency"):
                        final["currency"] = final["currency"].upper()

                    if not number_error:
                        issues = validate_invoice(final, existing_invoice_numbers())
                        status = save_invoice(uploaded_file.name, final, issues)
                        if issues:
                            st.warning("Saved with status: Needs review")
                            for issue in issues:
                                st.warning(issue)
                        else:
                            st.success("Saved with status: OK. No issues found.")

# ---------------- TAB 2: HISTORY ----------------
with tab_history:
    history = load_history()

    if history.empty:
        st.info("No invoices saved yet. Process an invoice first.")
    else:
        total_count = len(history)
        review_count = int((history["status"] == "Needs review").sum())
        c1, c2 = st.columns(2)
        c1.metric("Invoices processed", total_count)
        c2.metric("Need review", review_count)

        status_filter = st.selectbox("Show", ["All", "OK", "Needs review"])
        view = history if status_filter == "All" else history[history["status"] == status_filter]
        st.dataframe(view, width="stretch", hide_index=True)

        d1, d2 = st.columns(2)
        d1.download_button(
            "Download CSV",
            data=to_csv_bytes(view),
            file_name="invoices.csv",
            mime="text/csv",
        )
        d2.download_button(
            "Download Excel",
            data=to_excel_bytes(view),
            file_name="invoices.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        with st.expander("Delete a record"):
            delete_id = st.selectbox("Choose record ID", history["id"].tolist())
            if st.button("Delete selected record"):
                delete_invoice(delete_id)
                st.rerun()
