import streamlit as st
from pypdf import PdfReader

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
        for page in reader.pages[10:13]:
            all_text = all_text + page.extract_text() + "\n"

        st.subheader("Text from pages 11 to 13")
        st.text(all_text)