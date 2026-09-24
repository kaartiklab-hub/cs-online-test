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
QUESTIONS_CSV = "Class_12_CS_Evaluation_Part_I_Chapters_1_to_16_2.csv"
STUDENTS_CSV = "Student_Database.csv"
NUMBER_OF_QUESTIONS = 5 
# ==========================================

# --- CUSTOM BRANDING & FOOTER ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .custom-footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        color: #555555;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        font-weight: 600;
        border-top: 1px solid #eaeaea;
        z-index: 100;
    }
    </style>
    <div class="custom-footer">
        Crafted by [Your Name / Department] | Mt. St. Joseph Mat. Hr. Sec. School
    </div>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)
# ---------------------------------

# 1. Connect to Google Sheets
@st.cache_resource
def connect_to_gsheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Student_Results").sheet1

sheet = connect_to_gsheets()

if date.today() != TEST_DATE:
    st.error(f"🛑 This test is locked. It is only accessible on {TEST_DATE.strftime('%d %B %Y')}.")
    st.stop()

# Load ALL Questions
@st.cache_data
def load_all_questions():
    try:
        df = pd.read_csv(QUESTIONS_CSV, encoding="latin1")
        df.columns = df.columns.str.strip()
        if 'Chapter_No' in df.columns:
            df.rename(columns={'Chapter_No': 'Chapter'}, inplace=True)
        return df
    except FileNotFoundError:
        st.error(f"File '{QUESTIONS_CSV}' not found.")
        st.stop()

# Load Student Database
@st.cache_data
def load_student_database():
    try:
        return pd.read_csv(STUDENTS_CSV, dtype=str)
    except FileNotFoundError:
        st.error(f"File '{STUDENTS_CSV}' not found.")
        st.stop()

# Basic Session State Initialization
if 'student_info_submitted' not in st.session_state:
    st.session_state.student_info_submitted = False
    st.session_state.test_submitted = False
    st.session_state.user_answers = {}
    st.session_state.row_index = None
    st.session_state.assigned_indices = []
    st.session_state.questions_data = None

st.title("🏫 Mt. St. Joseph Mat. Hr. Sec. School")
st.subheader("Quarterly Holiday - Online Test")
st.divider()

# Login / Authentication Screen
if not st.session_state.student_info_submitted:
    st.markdown("### 🔒 Student Authentication")
    st.write("Please enter your registered credentials to access the exam.")
    
    roll_input = st.text_input("Roll Number")
    mobile_input = st.text_input("Registered Mobile Number")
    
    if st.button("Authenticate & Start Test", type="primary"):
        if roll_input.strip() == "" or mobile_input.strip() == "":
            st.warning("⚠️ Please fill in both fields.")
        else:
            full_df = load_all_questions()
            students_df = load_student_database()
            
            match = students_df[(students_df['Roll_no'].str.strip() == roll_input.strip()) & 
                                (students_df['Mobile_no'].str.strip() == mobile_input.strip())]
            
            if match.empty:
                st.error("❌ Authentication Failed: Invalid Roll Number or Mobile Number.")
            else:
                st.session_state.student_name = match.iloc[0]['Name_Student']
                st.session_state.roll_no = roll_input.strip()
                
                records = sheet.get_all_records()
                existing_row = None
                
                # Check for existing progress
                for i, record in enumerate(records):
                    if str(record.get('Roll_no')) == st.session_state.roll_no:
                        existing_row = i + 2 
                        if record.get('Status') == 'Completed':
                            st.error(f"Welcome {st.session_state.student_name}, but our records show you have already submitted this test.")
                            st.stop()
                        else:
                            saved_data_str = record.get('Saved_Answers')
                            if saved_data_str:
                                try:
                                    # Load BOTH the assigned questions and the answers
                                    saved_data = json.loads(saved_data_str)
                                    if "assigned" in saved_data:
                                        st.session_state.assigned_indices = saved_data["assigned"]
                                        st.session_state.user_answers = {int(k): v for k, v in saved_data["answers"].items()}
                                except json.JSONDecodeError:
                                    pass
                        break
                
                # If completely new attempt
                if not existing_row:
                    # 1. Generate the random questions exactly ONCE
                    st.session_state.assigned_indices = full_df.sample(n=min(NUMBER_OF_QUESTIONS, len(full_df))).index.tolist()
                    
                    # 2. Pack the question list into the save file immediately
                    initial_save = {"assigned": st.session_state.assigned_indices, "answers": {}}
                    new_row = [st.session_state.student_name, st.session_state.roll_no, "In Progress", json.dumps(initial_save), str(date.today()), ""]
                    
                    sheet.append_row(new_row)
                    st.session_state.row_index = len(records) + 2
                else:
                    st.session_state.row_index = existing_row
                
                # Build the dataframe using the explicitly assigned random questions
                st.session_state.questions_data = full_df.loc[st.session_state.assigned_indices].reset_index(drop=True)
                    
                st.success(f"✅ Welcome, {st.session_state.student_name}!")
                st.session_state.student_info_submitted = True
                st.rerun()

# Test Screen
elif st.session_state.student_info_submitted and not st.session_state.test_submitted:
    
    df = st.session_state.questions_data
    
    st.write(f"👤 **Student:** {st.session_state.student_name} | **Roll No:** {st.session_state.roll_no}")
    st.write("Ensure you click 'Save Progress' if your connection is unstable.")
    st.write("")
    
    for index, row in df.iterrows():
        st.markdown(f"**Q{index + 1}. {row['Question']}** *(Chapter: {row.get('Chapter', 'N/A')})*")
        options = [str(row['Option A']), str(row['Option B']), str(row['Option C']), str(row['Option D'])]
        
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

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Progress"):
            # Save BOTH the assigned questions and the current answers to the cloud
            save_data = {
                "assigned": st.session_state.assigned_indices,
                "answers": st.session_state.user_answers
            }
            sheet.update_cell(st.session_state.row_index, 4, json.dumps(save_data))
            st.toast("Progress saved to cloud!")
            
    with col2:
        if st.button("📤 Submit Final Test", type="primary"):
            if len(st.session_state.user_answers) < len(df):
                st.warning("⚠️ Please answer all questions before submitting.")
            else:
                st.session_state.test_submitted = True
                st.rerun()
    st.write("") 
    st.write("")

# Final Evaluation Screen
elif st.session_state.test_submitted:
    df = st.session_state.questions_data
    score = 0
    for index, row in df.iterrows():
        user_ans = st.session_state.user_answers.get(index)
        if str(user_ans).strip().lower() == str(row['Correct Answer']).strip().lower():
            score += 1

    total_questions = len(df)
    
    sheet.update_cell(st.session_state.row_index, 3, "Completed") 
    sheet.update_cell(st.session_state.row_index, 6, f"{score}/{total_questions}") 
    
    st.success("✅ Test Submitted Successfully!")
    st.write("Your results have been securely recorded in the teacher's database. You may now close this window.")
    st.metric(label="Your Final Score", value=f"{score} / {total_questions}")
