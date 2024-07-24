import streamlit as st
from PIL import Image
from PyPDF2 import PdfReader
from langchain_aws import BedrockLLM
import boto3
import pytesseract
from langdetect import detect

# Configurar cliente de LLM
aws_region = 'us-east-1'
bedrock_client = boto3.client('bedrock-runtime', region_name=aws_region)

def load_llm():
    """Load the Bedrock LLM."""
    return BedrockLLM(model_id="mistral.mixtral-8x7b-instruct-v0:1", client=bedrock_client)

llm = load_llm()

# Base de datos en memoria para indexar el contenido
database = {}

def extract_text_from_image(image):
    """Extract text from an image using OCR."""
    text = pytesseract.image_to_string(image)
    return text

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    reader = PdfReader(pdf_file)
    text = []
    for page in reader.pages:
        text.append(page.extract_text())
    return "\n".join(text)

def index_content(file_name, content):
    """Index the content of the file in the database."""
    database[file_name] = content

def retrieve_content():
    """Retrieve all indexed content."""
    return "\n".join(database.values())

def detect_language(text):
    """Detect the language of a given text."""
    return detect(text)

def run():
    st.header('Extract Text from Files')
    
    user_query_initial = st.text_input("Ask a question before uploading any file")
    if st.button("Ask Initial Query") and user_query_initial:
        language = detect_language(user_query_initial)
        prompt_initial = f"Query: {user_query_initial}\nPlease respond in {language}."
        try:
            query_response = llm.generate(prompts=[prompt_initial], temperature=0.1)
            if query_response.generations:
                llm_response = query_response.generations[0][0].text.strip()
                if llm_response == "":
                    llm_response = f"I don't have any information regarding that query in {language}."
                st.text_area('Initial LLM Response:', value=llm_response, height=200)
            else:
                st.error("No response was provided.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

    uploaded_file = st.file_uploader("Upload a file", type=["jpg", "jpeg", "png", "pdf"])
    file_content = None

    if uploaded_file is not None:
        if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(uploaded_file)
            file_content = extract_text_from_image(image)
        elif uploaded_file.type == "application/pdf":
            file_content = extract_text_from_pdf(uploaded_file)
        
        if file_content:
            index_content(uploaded_file.name, file_content)
            st.write("File content extracted and indexed.")

    user_query_followup = st.text_input("Ask a question about the indexed text")
    if st.button("Ask Follow-up Query") and user_query_followup:
        indexed_content = retrieve_content()
        language = detect_language(user_query_followup)
        prompt_followup = f"Based on the following indexed text, answer the query:\n\nIndexed Text: {indexed_content}\n\nQuery: {user_query_followup}\nPlease respond in {language}."
        try:
            query_response = llm.generate(prompts=[prompt_followup], temperature=0.1)
            if query_response.generations:
                llm_response = query_response.generations[0][0].text.strip()
                if llm_response == "":
                    llm_response = f"I don't have any information regarding that query in {language}."
                st.text_area('Follow-up LLM Response:', value=llm_response, height=200)
            else:
                st.error("No response was provided.")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == '__main__':
    run()
