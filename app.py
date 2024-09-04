import streamlit as st
import speech_recognition as sr
import pyttsx3
import google.generativeai as genai
from dotenv import load_dotenv
import os
import markdown
import io
import pandas as pd
from PyPDF2 import PdfReader  # Updated import for PdfReader
from docx import Document

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize recognizer and text-to-speech engine
recognizer = sr.Recognizer()
tts_engine = pyttsx3.init()

# Configure Streamlit page settings
st.set_page_config(
    page_title="Chat With Bot Using Voice",
    page_icon="😼",
    layout="centered",
)

# Initialize session state for chat history and file content if not already present
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_content" not in st.session_state:
    st.session_state.file_content = ""

def llm(text):
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(text)
        formatted_text = response.text.strip()
        return formatted_text
    except Exception as e:
        st.error(f"Error in LLM request: {e}")
        return "Sorry, I couldn't process your request."

def capitalize_first_letter(text):
    if not text:
        return text
    return text[0].upper() + text[1:]

def recognize_speech_from_microphone(listening_placeholder):
    with sr.Microphone() as source:
        listening_placeholder.info("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        try:
            audio = recognizer.record(source, duration=5)
            text = recognizer.recognize_google(audio)
            formatted_text = capitalize_first_letter(text)
            st.session_state.chat_history.append({"role": "user", "text": formatted_text})
            listening_placeholder.empty()
            return formatted_text
        except sr.UnknownValueError:
            listening_placeholder.error("Could not understand the audio")
        except sr.RequestError:
            listening_placeholder.error("Could not request results from the service")
        return None

def speak_text(text):
    if tts_engine._inLoop:
        tts_engine.endLoop()
    tts_engine.say(text)
    tts_engine.runAndWait()

def handle_file_upload(uploaded_file):
    if uploaded_file is not None:
        content = ""
        try:
            if uploaded_file.type == "text/plain":
                content = uploaded_file.read().decode("utf-8")
            elif uploaded_file.type == "application/pdf":
                pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))  # Updated to PdfReader
                for page in pdf_reader.pages:
                    content += page.extract_text()
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = Document(io.BytesIO(uploaded_file.read()))
                for para in doc.paragraphs:
                    content += para.text + "\n"
            elif uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
                content = df.to_string(index=False)
            elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                df = pd.read_excel(uploaded_file)
                content = df.to_string(index=False)
            else:
                st.error("Unsupported file type")
        except Exception as e:
            st.error(f"Error reading file: {e}")
        
        st.session_state.file_content = content

# Streamlit app UI
st.sidebar.title("Options")

# File uploader in sidebar
uploaded_file = st.sidebar.file_uploader("Choose a file", type=["txt", "pdf", "docx", "csv", "xlsx"])
if uploaded_file:
    handle_file_upload(uploaded_file)

if st.sidebar.button("Start New Conversation"):
    st.session_state.chat_history = []
    st.session_state.file_content = ""

st.title("Speech to Speech ChatBot")
st.write("Click the microphone button to speak.")

if st.button("🎤 Start Talking"):
    listening_placeholder = st.empty()
    recognized_text = recognize_speech_from_microphone(listening_placeholder)
    if recognized_text:
        # Combine recognized text with file content if available
        combined_text = f"{st.session_state.file_content}\n\nUser Query: {recognized_text}" if st.session_state.file_content else recognized_text

        with st.spinner("Processing..."):
            processed_text = llm(combined_text)
            st.session_state.chat_history.append({"role": "assistant", "text": processed_text})
        
        st.subheader("Chat History")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["text"])
        
        processed_text = markdown.markdown(processed_text)
        speak_text(processed_text)