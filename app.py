import streamlit as st
import pandas as pd
from datetime import date
import urllib.parse

# ==========================================
# CONFIGURATION
# ==========================================
TEST_DATE = date.today()
WHATSAPP_NUMBER = "918015220441" # Replace with actual number

# ⚠️ IMPORTANT: Keep your absolute path here if that is what fixed it!
CSV_FILENAME = "Class_12_CS_Evaluation_Part_I_Chapters_1_to_16_2.csv"

# 2) For testing, set to 5. Change this back to 100 for deployment.
NUMBER_OF_QUESTIONS = 5 
# ==========================================

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
        st.error(f"File '{CSV_FILENAME}' not found. Please check the file path.")
        st.stop()

# Initialize session states
if 'questions_data' not in st.session_state:
    st.session_state.questions_data = load_and_randomize_questions()
    st.session_state.user_answers = {}
    st.session_state.test_submitted = False
    st.session_state.student_info_submitted = False

df = st.session_state.questions_data

# 3) Updated Headings
st.title("🏫 Mt. St. Joseph Mat. Hr. Sec. School")
st.subheader("Quarterly Holiday - Online Test")
st.divider()

# 1) Get Student Name and Section before starting
if not st.session_state.student_info_submitted:
    st.markdown("### Please enter your details to begin")
    
    student_name = st.text_input("Student's Name")
    student_section = st.selectbox("Section", options=["Select Section", "A", "B", "C", "D", "E"])
    
    if st.button("Start Test", type="primary"):
        if student_name.strip() == "" or student_section == "Select Section":
            st.warning("⚠️ Please enter your Name and select a Section to continue.")
        else:
            st.session_state.student_name = student_name.strip()
            st.session_state.student_section = student_section
            st.session_state.student_info_submitted = True
            st.rerun()

# Display the test only if student info is submitted and test is not yet submitted
elif st.session_state.student_info_submitted and not st.session_state.test_submitted:
    
    st.write(f"👤 **Student:** {st.session_state.student_name} | **Section:** {st.session_state.student_section}")
    st.write("Please answer all questions before submitting.")
    st.write("")
    
    for index, row in df.iterrows():
        st.markdown(f"**Q{index + 1}. {row['Question']}** *(Chapter: {row.get('Chapter', 'N/A')})*")
        
        options = [str(row['Option A']), str(row['Option B']), str(row['Option C']), str(row['Option D'])]
        
        selected = st.radio(
            label="Select your answer",
            options=options,
            key=f"q_{index}",
            index=None,
            label_visibility="collapsed"
        )
        st.session_state.user_answers[index] = selected
        st.write("") 

    if st.button("Submit Test", type="primary"):
        if None in st.session_state.user_answers.values() or len(st.session_state.user_answers) < len(df):
            st.warning("⚠️ Please answer all questions before submitting.")
        else:
            st.session_state.test_submitted = True
            st.rerun()

# Evaluate and display results
elif st.session_state.test_submitted:
    score = 0
    for index, row in df.iterrows():
        user_ans = st.session_state.user_answers.get(index)
        if str(user_ans).strip().lower() == str(row['Correct Answer']).strip().lower():
            score += 1

    total_questions = len(df)
    
    st.success("✅ Test Submitted Successfully!")
    st.write(f"👤 **Student:** {st.session_state.student_name} | **Section:** {st.session_state.student_section}")
    st.metric(label="Your Final Score", value=f"{score} / {total_questions}")
    
    # WhatsApp Report updated with student details
    report_message = (
        f"*Quarterly Holiday - Online Test*\n"
        f"School: Mt. St. Joseph Mat. Hr. Sec. School\n"
        f"Name: {st.session_state.student_name}\n"
        f"Section: {st.session_state.student_section}\n"
        f"Score: {score}/{total_questions}\n"
        f"Date: {date.today().strftime('%d %b %Y')}"
    )
    
    encoded_message = urllib.parse.quote(report_message)
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_message}"
    
    st.markdown("### Next Step:")
    st.markdown(
        f"""
        <a href="{whatsapp_url}" target="_blank">
            <button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-size:16px; font-weight:bold; cursor:pointer; width:100%;">
                Send Report to Teacher via WhatsApp 📲
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )