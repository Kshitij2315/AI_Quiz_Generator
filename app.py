import os
import streamlit as st 
from utils import extract_text_from_pdf, generate_quiz, generate_ai_coaching_report

if "GOOGLE_API_KEY" in st.secrets:
    os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]
else:
    st.sidebar.warning("GOOGLE_API_KEY not found! Please add it to your .streamlit/secrets.toml file or Streamlit Cloud panel.")

st.set_page_config(
    page_title="AI Mini-Quiz Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title("AI Mini-Quiz Generator")

st.sidebar.header("Quiz Settings")
mode = st.sidebar.radio("Generation Mode", ["Topic", "Upload PDF Document"])

st.sidebar.subheader("Question Distribution")
easy_count = st.sidebar.slider("Easy Question Count", 0, 5, 0)
medium_count = st.sidebar.slider("Medium Question Count", 0, 5, 0)
hard_count = st.sidebar.slider("Hard Question Count", 0, 5, 0)
total_questions = easy_count + medium_count + hard_count

source_material = ""
is_rag_active = False

if mode == "Topic":
    source_material = st.sidebar.text_input("Enter Quiz Topic", placeholder="General Knowledge, Python, World History", help="Provide a clear topic for the quiz generation.")
else:
    is_rag_active = True
    uploaded_file = st.sidebar.file_uploader("Upload PDF Document (Max 10 Pages)", type=["pdf"], help="To maintain high quiz quality and prevent token limits, please upload documents up to 10 pages.")
    if uploaded_file:
        with st.sidebar.spinner("Reading entire PDF..."):
            try:
                source_material = extract_text_from_pdf(uploaded_file)
                st.sidebar.success("PDF loaded! All pages processed successfully.")
            except ValueError as e:
                st.sidebar.error(str(e))
                source_material = ""

if st.sidebar.button("Generate Quiz", disabled=not source_material or total_questions == 0):
    with st.spinner("Generating quiz questions, please wait..."):
        try:
            quiz_result = generate_quiz(source_material, easy_count, medium_count, hard_count, is_rag_active)
            st.session_state.generated_quiz = quiz_result
            st.session_state.user_answers = {}
            st.session_state.quiz_completed = False
            st.session_state.coaching_report = None
            st.rerun()
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "limit" in error_msg or "exhausted" in error_msg or "429" in error_msg:
                st.error("**Too Many Requests!** The AI service is currently at full capacity due to high usage limits. Please wait a minute or two and try generating your quiz again!")
            else:
                st.error(f"Quiz generation failed: {e}")

if "generated_quiz" in st.session_state:
    quiz = st.session_state.generated_quiz
    tab_exam, tab_analysis = st.tabs(["Quiz Area", "Analysis and AI Coaching"])
    
    with tab_exam:
        st.header(f"{quiz.quiz_title}")
        st.info(f"Total Questions: {len(quiz.questions)} | Distribution: {easy_count} Easy, {medium_count} Medium, {hard_count} Hard")
        temp_answers = {}
        
        with st.form(key="quiz_form"):
            for idx, q in enumerate(quiz.questions):
                diff_emoji = "🟢" if q.difficulty == "Easy" else "🟡" if q.difficulty == "Medium" else "🔴"
                st.markdown(f"### {diff_emoji} Question {idx+1}", unsafe_allow_html=True)
                st.write(q.question)

                temp_answers[idx] = st.radio(
                    f"Select the correct option (Question {idx+1}):",
                    options=q.options,
                    key=f"radio_{idx}",
                    index=None,
                    label_visibility="collapsed"
                )
                st.write("---")
                
            submit_button = st.form_submit_button(label="Finish Quiz and Submit Results")
            
            if submit_button:
                st.session_state.user_answers = temp_answers
                st.session_state.quiz_completed = True

                with st.spinner("AI Coaching is analyzing your performance..."):
                    try:
                        st.session_state.coaching_report = generate_ai_coaching_report(quiz, st.session_state.user_answers)
                        st.rerun()
                    except Exception as e:
                        error_msg = str(e).lower()
                        if "quota" in error_msg or "limit" in error_msg or "exhausted" in error_msg or "429" in error_msg:
                            st.warning("**Quiz submitted successfully, but AI Coaching is resting!** We saved your results, but the AI API quota limit is temporarily reached. Please refresh the page or wait a moment to see your analysis report.")
                        else:
                            st.error(f"Analysis failed: {e}")


    with tab_analysis:
        if not st.session_state.quiz_completed:
            st.warning("Please solve the quiz from the 'Quiz Area' tab and click the 'Finish Quiz' button.")
        else:
            st.header("Quiz Results Report")
            
            correct_count = 0
            for idx, q in enumerate(quiz.questions):
                if st.session_state.user_answers.get(idx) == q.correct_answer:
                    correct_count += 1
            
            wrong_count = len(quiz.questions) - correct_count
            score_percentage = int((correct_count / len(quiz.questions)) * 100) if len(quiz.questions) > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Correct Answers", f"{correct_count} / {len(quiz.questions)}")
            col2.metric("Wrong/Empty", f"{wrong_count}")
            col3.metric("Success Rate", f"%{score_percentage}")
            
            st.write("---")
            
            st.subheader("AI Coaching Analysis")
            if st.session_state.coaching_report:
                st.info(st.session_state.coaching_report)
            
            st.write("---")
            st.subheader("Question Detail Reviews")
            
            for idx, q in enumerate(quiz.questions):
                user_ans = st.session_state.user_answers.get(idx)
                is_correct = user_ans == q.correct_answer

                if is_correct:
                    status_text = "✅ Correct"
                elif user_ans is None or user_ans == "Left Empty" or user_ans == "":
                    status_text = "⚪ Empty" 
                else:
                    status_text = "❌ Wrong"
                
                expander_title = f"Question {idx+1}: {status_text}"
                with st.expander(expander_title):
                    st.markdown(f"**Question:** {q.question}")
                    st.write(f"**Your Answer:** {user_ans if user_ans else 'Left Empty'}")
                    st.write(f"**Correct Answer:** {q.correct_answer}")
                    
                    if is_correct:
                        st.success("Correct Answer Explanation:")
                        st.write(q.explanation)
                    else:
                        st.error("Question Review & Explanation:")
                        st.write(q.explanation)
else:
    st.info("Welcome! To create a quiz, please enter a topic title from the menu on the left or upload your PDF file, then click the 'Generate Quiz' button.")