import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
import json

# ==========================================
# CONFIGURATION
# ==========================================
TEST_DATE = date.today()
CSV_FILENAME = "Class_12_CS_Evaluation_Part_I_Chapters_1_to_16_2.csv"
NUMBER_OF_QUESTIONS = 5 
# ==========================================

# 1. Connect to Google Sheets
@st.cache_resource
def connect_to_gsheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Loads credentials from the .streamlit/secrets.toml file
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    # Open the Google Sheet by its exact name
    return client.open("Student_Results").sheet1

sheet = connect_to_gsheets()

# Enforce date
if date.today() != TEST_DATE:
    st.error(f"🛑 This test is locked. It is only accessible on {TEST_DATE.strftime('%d %B %Y')}.")
    st.stop()

@st.cache_data
def load_and_randomize_questions():
    try:
        df = pd.read_csv(CSV_FILENAME, encoding="latin1")
        df.columns = df.columns.str.strip()
        if 'Chapter_No' in df.columns:
            df.rename(columns={'Chapter_No': 'Chapter'}, inplace=True)
            
        sample_size = min(NUMBER_OF_QUESTIONS, len(df))
        randomized_df = df.sample(n=sample_size).reset_index(drop=True)
        return randomized_df
    except FileNotFoundError:
        st.error(f"File '{CSV_FILENAME}' not found.")
        st.stop()

# Initialize basic session state
if 'questions_data' not in st.session_state:
    st.session_state.questions_data = load_and_randomize_questions()
    st.session_state.student_info_submitted = False
    st.session_state.test_submitted = False
    st.session_state.user_answers = {}
    st.session_state.row_index = None

df = st.session_state.questions_data

st.title("🏫 Mt. St. Joseph Mat. Hr. Sec. School")
st.subheader("Quarterly Holiday - Online Test")
st.divider()

# Login / Resume Screen
if not st.session_state.student_info_submitted:
    st.markdown("### Please enter your details to begin")
    
    student_name = st.text_input("Student's Name")
    student_section = st.selectbox("Section", options=["Select Section", "A", "B", "C", "D", "E"])
    
    if st.button("Start / Resume Test", type="primary"):
        if student_name.strip() == "" or student_section == "Select Section":
            st.warning("⚠️ Please enter your Name and select a Section.")
        else:
            st.session_state.student_name = student_name.strip()
            st.session_state.student_section = student_section
            
            # --- Check Google Sheet for Existing Student ---
            records = sheet.get_all_records()
            existing_row = None
            
            for i, record in enumerate(records):
                if record.get('Name') == st.session_state.student_name and record.get('Section') == st.session_state.student_section:
                    existing_row = i + 2 # +2 because row 1 is headers and zero-indexed
                    if record.get('Status') == 'Completed':
                        st.error("You have already completed and submitted this test.")
                        st.stop()
                    else:
                        # Load previously saved answers to resume
                        saved_answers = record.get('Saved_Answers')
                        if saved_answers:
                            # Convert JSON string back to dictionary integers
                            loaded_dict = json.loads(saved_answers)
                            st.session_state.user_answers = {int(k): v for k, v in loaded_dict.items()}
                    break
            
            # If student is new, create a new row in Google Sheets
            if not existing_row:
                new_row = [st.session_state.student_name, st.session_state.student_section, "In Progress", "", str(date.today())]
                # Assuming Sheet Headers: Name | Section | Status | Saved_Answers | Date | Score
                if len(records) == 0:
                    sheet.append_row(["Name", "Section", "Status", "Saved_Answers", "Date", "Score"])
                sheet.append_row(new_row)
                st.session_state.row_index = len(records) + 2
            else:
                st.session_state.row_index = existing_row
                
            st.session_state.student_info_submitted = True
            st.rerun()

# Test Screen
elif st.session_state.student_info_submitted and not st.session_state.test_submitted:
    
    st.write(f"👤 **Student:** {st.session_state.student_name} | **Section:** {st.session_state.student_section}")
    st.write("Ensure you click 'Save Progress' if your connection is unstable.")
    
    for index, row in df.iterrows():
        st.markdown(f"**Q{index + 1}. {row['Question']}** *(Chapter: {row.get('Chapter', 'N/A')})*")
        options = [str(row['Option A']), str(row['Option B']), str(row['Option C']), str(row['Option D'])]
        
        # Pre-select answer if they are resuming
        pre_selected = st.session_state.user_answers.get(index)
        default_index = options.index(pre_selected) if pre_selected in options else None
        
        selected = st.radio(
            label="Select your answer",
            options=options,
            key=f"q_{index}",
            index=default_index,
            label_visibility="collapsed"
        )
        if selected is not None:
             st.session_state.user_answers[index] = selected
        st.write("") 

    col1, col2 = st.columns(2)
    
    with col1:
        # Button to save current state to Google Sheets mid-test
        if st.button("💾 Save Progress"):
            answers_json = json.dumps(st.session_state.user_answers)
            # Update the 'Saved_Answers' column (assuming it is column D / 4)
            sheet.update_cell(st.session_state.row_index, 4, answers_json)
            st.toast("Progress saved to cloud!")
            
    with col2:
        if st.button("📤 Submit Final Test", type="primary"):
            if len(st.session_state.user_answers) < len(df):
                st.warning("⚠️ Please answer all questions before submitting.")
            else:
                st.session_state.test_submitted = True
                st.rerun()

# Final Evaluation Screen
elif st.session_state.test_submitted:
    score = 0
    for index, row in df.iterrows():
        user_ans = st.session_state.user_answers.get(index)
        if str(user_ans).strip().lower() == str(row['Correct Answer']).strip().lower():
            score += 1

    total_questions = len(df)
    
    # Update Google Sheet with final score and lock the status
    sheet.update_cell(st.session_state.row_index, 3, "Completed") # Update Status
    sheet.update_cell(st.session_state.row_index, 6, f"{score}/{total_questions}") # Update Score
    
    st.success("✅ Test Submitted Successfully!")
    st.write("Your results have been securely recorded in the teacher's database. You may now close this window.")
    st.metric(label="Your Final Score", value=f"{score} / {total_questions}")
