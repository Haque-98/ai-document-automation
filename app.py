import streamlit as st

st.title("AI Document Automation")
st.write("Welcome to my AI Document Automation System")

uploaded_file = st.file_uploader("Upload an invoice", type=["pdf", "jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.success("File uploaded: " + uploaded_file.name)
    st.write("File type:", uploaded_file.type)
    st.write("File size (bytes):", uploaded_file.size)