import streamlit as st
import pytesseract
from PIL import Image
from pypdf import PdfReader

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\buth\AppData\Local\Tesseract-OCR\tesseract.exe"

st.title("AI Document Automation")
st.write("Welcome to my AI Document Automation System")

uploaded_file = st.file_uploader("Upload an invoice", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.success("File uploaded: " + uploaded_file.name)
    st.write("File type:", uploaded_file.type)
    st.write("File size (bytes):", uploaded_file.size)

    if uploaded_file.type == "application/pdf":
        reader = PdfReader(uploaded_file)
        st.write("Total pages:", len(reader.pages))

        all_text = ""
        for page in reader.pages[:3]:
            all_text = all_text + page.extract_text() + "\n"

        st.subheader("Text from first 3 pages")
        st.text(all_text)

    else:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded image")

        ocr_text = pytesseract.image_to_string(image)
        st.subheader("Text from image (OCR)")
        st.text(ocr_text)