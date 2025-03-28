import streamlit as st
import speech_recognition as sr
import pandas as pd
from db_handler import execute_query
from ai_generator import get_gemini_response
from schema_handler import load_schema
from apply_UI import global_page_style
from deep_translator import GoogleTranslator

st.set_page_config(page_title="Query Wizard", layout="wide", page_icon="logo.png")

global_page_style()  # Apply global CSS

st.title("Query Wizard")

# Load Schema (Table Names)
schema = load_schema()
tables = list(schema.keys())

# Sidebar: Show list of tables
st.sidebar.image("logo.jpg", use_container_width=True)  # Updated parameter
selected_table = st.sidebar.selectbox("📌 Select a Table:", ["None"] + list(schema.keys()))

if "uploaded_data" not in st.session_state:
    st.session_state["uploaded_data"] = None

def translate_prompt(text):
    """
    Translates the user input into English while preserving table names.
    """
    translator = GoogleTranslator(source='auto', target='en')
    try:
        return translator.translate(text)
    except Exception as e:
        st.error(f"Translation Error: {e}")
        return text  

# State management for show/hide details
if "show_details" not in st.session_state:
    st.session_state["show_details"] = False  # Default: Hide details

if "generated_sql" not in st.session_state:
    st.session_state["generated_sql"] = ""

if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""
    

# Show structure of selected table (Field names & data types initially)
if selected_table and selected_table != "None":
    st.sidebar.markdown(f"### 📄 Schema Preview : `{selected_table}` ")
    table_columns = schema.get(selected_table, {})

    schema_df = pd.DataFrame([
        {"Column": col, "Data Type": details["type"]}
        for col, details in table_columns.items()
    ])

    # Display schema in a styled table
    st.sidebar.markdown(
        schema_df.style.set_table_styles(
            [{"selector": "th", "props": [("background-color", "#1E1E1E"),
                                        ("color", "white"),
                                        ("border", "1px solid white"),
                                        ("text-align", "left")]}]
        ).to_html(),
        unsafe_allow_html=True
    )
    # Toggle buttons for Show More / Hide Details
    if not st.session_state["show_details"]:
        if st.sidebar.button("SHOW SCHEMA"):
            st.session_state["show_details"] = True
            st.rerun()  # Refresh UI
    else:
        st.sidebar.subheader("Detailed Schema :")
        st.sidebar.json(table_columns)  # Show complete structure

        if st.sidebar.button("HIDE SCHEMA"):
            st.session_state["show_details"] = False
            st.rerun()  # Refresh UI

    # Button to display all records from the selected table
    if st.sidebar.button("DISPLAY ALL RECORDS"):
        query = f"SELECT * FROM {selected_table} LIMIT 100;"
        st.session_state["generated_sql"] = query
        execute_query(query)  # Display records on click

# Function to update user input
def update_user_input():
    st.session_state["user_input"] = st.session_state["input_text"]

# Speech-to-Text Function
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.write("🎙️ Listening... Please speak your query.")
        recognizer.adjust_for_ambient_noise(source, duration=1)  # Adjusts for background noise
        audio = recognizer.listen(source, timeout=None, phrase_time_limit=None)  # Listen indefinitely

    try:
        # Using Google's free API for speech recognition
        text = recognizer.recognize_google(audio)
        st.session_state["user_input"] = text
        st.success(f" You said: {text}")
    except sr.UnknownValueError:
        st.error(" Could not understand the speech.")
    except sr.RequestError as e:
        st.error(f"Could not request results from Google Speech Recognition service; {e}")

# def handle_file_upload():
#     uploaded_file = st.file_uploader("📂 Upload CSV File", type=["csv"])
#     if uploaded_file is not None:
#         df = pd.read_csv(uploaded_file)
#         st.session_state["uploaded_data"] = df
#         st.success(f"✅ File '{uploaded_file.name}' uploaded successfully!")

#         # Update the input field with file info (does not overwrite manual/voice input)
#         if st.session_state["user_input"].strip():
#             st.session_state["user_input"] += f"\nQuerying: {uploaded_file.name}"
#         else:
#             st.session_state["user_input"] = f"Querying: {uploaded_file.name}"

#         st.write(df.head())  # Show preview
        
# def execute_query_on_uploaded_data(query):
#     if st.session_state["uploaded_data"] is not None:
#         conn = sqlite3.connect(":memory:")  # In-memory SQLite database
#         st.session_state["uploaded_data"].to_sql("uploaded_table", conn, index=False, if_exists="replace")
#         try:
#             result_df = pd.read_sql_query(query, conn)
#             st.write("📊 Query Results:")
#             st.dataframe(result_df)
#         except Exception as e:
#             st.error(f"❌ Query Execution Error: {e}")
#         finally:
#             conn.close()
            
# User Input for AI Query Generation
st.subheader("Enter Prompt:")

# Text Area (Linked to Session State)
st.text_area(
    " ",
    key="input_text",  # Different key from session state
    value=st.session_state["user_input"],
    on_change=update_user_input
)

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("Clear"):
        st.session_state["user_input"] = ""  # Reset stored input
        st.session_state["input_text"] = ""  # Reset text area
        st.session_state["generated_sql"] = ""  # Reset query
        st.rerun()  # Refresh UI to clear input

# Button to capture speech input
with col1:
    if st.button("Voice Input"):
        speech_to_text()  # Capture and display speech input
    
# if st.button("➕"):
#     handle_file_upload()

col3, col4 = st.columns([4, 1])
# Generate SQL Query
with col3:
    if st.button("Generate SQL"):
        if st.session_state["user_input"]:
            # Translate the user input before passing to the AI model
            translated_input = translate_prompt(st.session_state["user_input"])
            sql_query = get_gemini_response(translated_input)  # Generate SQL using translated input
            if sql_query:
                st.session_state["generated_sql"] = sql_query
                st.subheader("Generated SQL Query")
                st.code(sql_query, language='sql')
            else:
                st.error("⚠️ Failed to generate query.")
        else:
            st.warning("⚠️ Please enter a query first.")

# Execute SQL Query
with col4:
    if st.button("Execute SQL"):
        if st.session_state["generated_sql"]:
            execute_query(st.session_state["generated_sql"])
        else:
            st.warning("⚠️ Generate a query first.")
