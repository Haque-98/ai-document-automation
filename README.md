# AI Document Automation System

A web app that reads business invoices (PDF, JPG, PNG), uses AI to extract the key fields into structured JSON, checks the data for problems, lets the user review and edit it, and stores everything in a searchable history with CSV and Excel export.

## Features

- Upload PDF, JPG and PNG invoices
- Text extraction: `pypdf` for text PDFs, Tesseract OCR for images
- AI extraction (Google Gemini) of: vendor name, invoice number, invoice date, due date, customer name, subtotal, tax amount, total amount, currency
- Validation: missing fields, subtotal + tax not equal to total, negative amounts, invalid dates, due date before invoice date, unusual currency, duplicate invoice numbers
- Review and edit form before saving
- Processing history stored in SQLite (status: OK or Needs review)
- Export to CSV and Excel
- Friendly error handling for corrupt files, scanned PDFs, empty images, and AI failures (with automatic retry)

## Architecture

```
Upload (PDF / JPG / PNG)
        |
Text extraction  (pypdf or Tesseract OCR)
        |
AI extraction    (Gemini API -> JSON)
        |
Validation       (rules written in Python)
        |
Human review     (editable form in Streamlit)
        |
SQLite database  (history)
        |
CSV / Excel export
```

## Tech Stack

- Python
- Streamlit (user interface)
- pypdf, Pillow, pytesseract (document reading and OCR)
- Google Gemini API via `google-genai` (AI extraction)
- SQLite (storage)
- pandas, openpyxl (CSV and Excel export)
- python-dotenv (API key management)

## Setup (Windows)

1. Install Python, Git and [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
2. Clone the repository and open the folder:
   ```
   git clone https://github.com/Haque-98/ai-document-automation.git
   cd ai-document-automation
   ```
3. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
4. Install the libraries:
   ```
   pip install -r requirements.txt
   ```
5. Create a file named `.env` (see `.env.example`) and add your own Gemini API key:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Optional settings: `GEMINI_MODEL` and `TESSERACT_PATH`.
6. Run the app:
   ```
   streamlit run app.py
   ```

## Security

- The API key is stored in `.env`, which is excluded from Git.
- The database (`invoices.db`) is excluded from Git.
- Only synthetic sample invoices should be used for testing and demos.

## Known Limitations

- Scanned PDFs are not supported yet (upload them as JPG or PNG instead).
- Only the first 3 pages of a PDF are processed.
- OCR quality depends on image quality.
- The AI service can be temporarily unavailable; the app retries automatically.

## Future Improvements

- Split the code into separate modules and add automated tests
- OCR fallback for scanned PDFs
- Support for line items
- Online deployment

## Author

Built by Haque-98 as a learning project in AI engineering.