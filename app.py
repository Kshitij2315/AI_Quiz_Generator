import os
import streamlit as st

from utils import (
    extract_text_from_pdf,
    generate_quiz,
    generate_ai_coaching_report
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Mini-Quiz Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# GROQ API KEY
# ============================================================

try:
    groq_api_key = st.secrets.get("GROQ_API_KEY")

    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key
    else:
        st.sidebar.warning(
            "GROQ_API_KEY not found. "
            "Please add it to .streamlit/secrets.toml."
        )

except Exception:
    st.sidebar.warning(
        "Could not load GROQ_API_KEY. "
        "Please check your .streamlit/secrets.toml file."
    )


# ============================================================
# TITLE
# ============================================================

st.title("AI Mini-Quiz Generator")


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.header("Quiz Settings")

mode = st.sidebar.radio(
    "Generation Mode",
    ["Topic", "Upload PDF Document"]
)


# ============================================================
# QUESTION DISTRIBUTION
# ============================================================

st.sidebar.subheader("Question Distribution")

easy_count = st.sidebar.slider(
    "Easy Question Count",
    0,
    5,
    0
)

medium_count = st.sidebar.slider(
    "Medium Question Count",
    0,
    5,
    0
)

hard_count = st.sidebar.slider(
    "Hard Question Count",
    0,
    5,
    0
)

total_questions = (
    easy_count +
    medium_count +
    hard_count
)


# ============================================================
# SOURCE MATERIAL
# ============================================================

source_material = ""
is_rag_active = False


# ============================================================
# TOPIC MODE
# ============================================================

if mode == "Topic":

    source_material = st.sidebar.text_input(
        "Enter Quiz Topic",
        placeholder="General Knowledge, Python, World History",
        help="Provide a clear topic for quiz generation."
    )


# ============================================================
# PDF MODE
# ============================================================

else:

    is_rag_active = True

    uploaded_file = st.sidebar.file_uploader(
        "Upload PDF Document (Max 10 Pages)",
        type=["pdf"],
        help="Upload a PDF containing the material for quiz generation."
    )

    if uploaded_file:

        with st.sidebar.spinner("Reading entire PDF..."):

            try:

                source_material = extract_text_from_pdf(
                    uploaded_file
                )

                st.sidebar.success(
                    "PDF loaded! All pages processed successfully."
                )

            except ValueError as e:

                st.sidebar.error(str(e))

                source_material = ""

            except Exception as e:

                st.sidebar.error(
                    f"Could not read the PDF: {e}"
                )

                source_material = ""


# ============================================================
# GENERATE QUIZ BUTTON
# ============================================================

generate_button = st.sidebar.button(
    "Generate Quiz",
    disabled=(
        not source_material or
        total_questions == 0 or
        not groq_api_key
    )
)


# ============================================================
# GENERATE QUIZ
# ============================================================

if generate_button:

    with st.spinner(
        "Generating quiz using Groq AI, please wait..."
    ):

        try:

            quiz_result = generate_quiz(
                source_material,
                easy_count,
                medium_count,
                hard_count,
                is_rag_active,
                groq_api_key
            )

            # Store quiz
            st.session_state.generated_quiz = quiz_result

            # Reset previous answers
            st.session_state.user_answers = {}

            # Reset completion status
            st.session_state.quiz_completed = False

            # Reset coaching report
            st.session_state.coaching_report = None

            st.rerun()

        except Exception as e:

            error_msg = str(e).lower()

            # ------------------------------------------------
            # GROQ RATE LIMIT / QUOTA
            # ------------------------------------------------

            if (
                "429" in error_msg
                or "rate limit" in error_msg
                or "rate_limit" in error_msg
                or "too many requests" in error_msg
                or "quota" in error_msg
            ):

                st.error(
                    "⚠️ **Groq API rate limit reached.**\n\n"
                    "Please wait for the limit to reset and try again."
                )

            # ------------------------------------------------
            # SERVICE UNAVAILABLE
            # ------------------------------------------------

            elif (
                "503" in error_msg
                or "service unavailable" in error_msg
                or "unavailable" in error_msg
            ):

                st.error(
                    "⚠️ **Groq service is temporarily unavailable.**\n\n"
                    "Please wait a moment and try again."
                )

            # ------------------------------------------------
            # AUTHENTICATION ERROR
            # ------------------------------------------------

            elif (
                "401" in error_msg
                or "authentication" in error_msg
                or "invalid api key" in error_msg
                or "api key" in error_msg
            ):

                st.error(
                    "❌ **Groq API key error.**\n\n"
                    "Check your GROQ_API_KEY in "
                    ".streamlit/secrets.toml."
                )

            # ------------------------------------------------
            # GENERAL ERROR
            # ------------------------------------------------

            else:

                st.error(
                    f"Quiz generation failed:\n\n{e}"
                )


# ============================================================
# DISPLAY GENERATED QUIZ
# ============================================================

if "generated_quiz" in st.session_state:

    quiz = st.session_state.generated_quiz

    tab_exam, tab_analysis = st.tabs(
        [
            "Quiz Area",
            "Analysis and AI Coaching"
        ]
    )


    # ========================================================
    # QUIZ TAB
    # ========================================================

    with tab_exam:

        st.header(
            quiz.quiz_title
        )

        st.info(
            f"Total Questions: {len(quiz.questions)} | "
            f"Distribution: "
            f"{easy_count} Easy, "
            f"{medium_count} Medium, "
            f"{hard_count} Hard"
        )

        temp_answers = {}


        # ====================================================
        # QUIZ FORM
        # ====================================================

        with st.form(key="quiz_form"):

            for idx, q in enumerate(quiz.questions):

                if q.difficulty == "Easy":
                    diff_emoji = "🟢"

                elif q.difficulty == "Medium":
                    diff_emoji = "🟡"

                else:
                    diff_emoji = "🔴"


                st.markdown(
                    f"### {diff_emoji} Question {idx + 1}"
                )

                st.write(
                    q.question
                )


                temp_answers[idx] = st.radio(
                    f"Select the correct option "
                    f"(Question {idx + 1}):",
                    options=q.options,
                    key=f"radio_{idx}",
                    index=None,
                    label_visibility="collapsed"
                )

                st.write("---")


            submit_button = st.form_submit_button(
                label="Finish Quiz and Submit Results"
            )


            # =================================================
            # SUBMIT QUIZ
            # =================================================

            if submit_button:

                st.session_state.user_answers = temp_answers

                st.session_state.quiz_completed = True


                # =================================================
                # AI COACHING
                # =================================================

                with st.spinner(
                    "Groq AI is analyzing your performance..."
                ):

                    try:

                        coaching_report = (
                            generate_ai_coaching_report(
                                quiz,
                                st.session_state.user_answers,
                                groq_api_key
                            )
                        )

                        st.session_state.coaching_report = (
                            coaching_report
                        )

                    except Exception as e:

                        error_msg = str(e).lower()

                        if (
                            "429" in error_msg
                            or "rate limit" in error_msg
                            or "rate_limit" in error_msg
                            or "too many requests" in error_msg
                            or "quota" in error_msg
                        ):

                            st.warning(
                                "**Quiz submitted successfully!**\n\n"
                                "However, the Groq AI Coaching report "
                                "could not be generated because "
                                "the Groq API rate limit was reached."
                            )

                        elif (
                            "503" in error_msg
                            or "service unavailable" in error_msg
                        ):

                            st.warning(
                                "**Quiz submitted successfully!**\n\n"
                                "The Groq AI Coaching service is "
                                "temporarily unavailable."
                            )

                        else:

                            st.error(
                                f"Analysis failed: {e}"
                            )

                st.rerun()


    # ========================================================
    # ANALYSIS TAB
    # ========================================================

    with tab_analysis:

        if not st.session_state.quiz_completed:

            st.warning(
                "Please solve the quiz from the "
                "'Quiz Area' tab and click "
                "'Finish Quiz'."
            )

        else:

            st.header(
                "Quiz Results Report"
            )


            # =================================================
            # SCORE CALCULATION
            # =================================================

            correct_count = 0

            for idx, q in enumerate(
                quiz.questions
            ):

                if (
                    st.session_state.user_answers.get(idx)
                    == q.correct_answer
                ):

                    correct_count += 1


            wrong_count = (
                len(quiz.questions)
                - correct_count
            )


            if len(quiz.questions) > 0:

                score_percentage = int(
                    (
                        correct_count /
                        len(quiz.questions)
                    ) * 100
                )

            else:

                score_percentage = 0


            # =================================================
            # SCORE DISPLAY
            # =================================================

            col1, col2, col3 = st.columns(3)


            col1.metric(
                "Correct Answers",
                f"{correct_count} / {len(quiz.questions)}"
            )


            col2.metric(
                "Wrong/Empty",
                f"{wrong_count}"
            )


            col3.metric(
                "Success Rate",
                f"{score_percentage}%"
            )


            st.write("---")


            # =================================================
            # AI COACHING
            # =================================================

            st.subheader(
                "AI Coaching Analysis"
            )


            if st.session_state.coaching_report:

                st.info(
                    st.session_state.coaching_report
                )

            else:

                st.info(
                    "AI Coaching report is not available."
                )


            st.write("---")


            # =================================================
            # QUESTION REVIEWS
            # =================================================

            st.subheader(
                "Question Detail Reviews"
            )


            for idx, q in enumerate(
                quiz.questions
            ):

                user_ans = (
                    st.session_state.user_answers.get(
                        idx
                    )
                )


                is_correct = (
                    user_ans == q.correct_answer
                )


                if is_correct:

                    status_text = "✅ Correct"

                elif (
                    user_ans is None
                    or user_ans == "Left Empty"
                    or user_ans == ""
                ):

                    status_text = "⚪ Empty"

                else:

                    status_text = "❌ Wrong"


                expander_title = (
                    f"Question {idx + 1}: "
                    f"{status_text}"
                )


                with st.expander(
                    expander_title
                ):

                    st.markdown(
                        f"**Question:** {q.question}"
                    )


                    st.write(
                        "**Your Answer:** "
                        f"{user_ans if user_ans else 'Left Empty'}"
                    )


                    st.write(
                        "**Correct Answer:** "
                        f"{q.correct_answer}"
                    )


                    if is_correct:

                        st.success(
                            "Correct Answer Explanation:"
                        )

                        st.write(
                            q.explanation
                        )

                    else:

                        st.error(
                            "Question Review & Explanation:"
                        )

                        st.write(
                            q.explanation
                        )


# ============================================================
# WELCOME MESSAGE
# ============================================================

else:

    st.info(
        "Welcome! To create a quiz, please enter "
        "a topic from the menu on the left or "
        "upload your PDF file, then click "
        "'Generate Quiz'."
    )