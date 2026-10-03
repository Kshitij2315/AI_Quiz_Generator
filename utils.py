from typing import List
import json

from pydantic import BaseModel, Field
from pypdf import PdfReader
from groq import Groq


# ============================================================
# QUIZ DATA MODELS
# ============================================================

class QuizQuestion(BaseModel):
    question: str = Field(
        description="The multiple-choice question text."
    )

    options: List[str] = Field(
        description="Exactly 5 multiple-choice options."
    )

    correct_answer: str = Field(
        description="The exact string of the correct option."
    )

    explanation: str = Field(
        description="A clear explanation of why the answer is correct."
    )

    difficulty: str = Field(
        description="Difficulty of the question: Easy, Medium, or Hard."
    )


class FullQuiz(BaseModel):
    quiz_title: str = Field(
        description="A clear academic title for the quiz."
    )

    questions: List[QuizQuestion] = Field(
        description="Generated quiz questions."
    )


# ============================================================
# GROQ CONFIGURATION
# ============================================================

MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# CREATE GROQ CLIENT
# ============================================================

def get_groq_client(api_key: str):
    return Groq(api_key=api_key)


# ============================================================
# GROQ JSON SCHEMA
# ============================================================

QUIZ_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "quiz_title": {
            "type": "string"
        },

        "questions": {
            "type": "array",

            "items": {
                "type": "object",
                "additionalProperties": False,

                "properties": {
                    "question": {
                        "type": "string"
                    },

                    "options": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },

                    "correct_answer": {
                        "type": "string"
                    },

                    "explanation": {
                        "type": "string"
                    },

                    "difficulty": {
                        "type": "string",
                        "enum": [
                            "Easy",
                            "Medium",
                            "Hard"
                        ]
                    }
                },

                "required": [
                    "question",
                    "options",
                    "correct_answer",
                    "explanation",
                    "difficulty"
                ]
            }
        }
    },

    "required": [
        "quiz_title",
        "questions"
    ]
}


# ============================================================
# GENERATE QUIZ
# ============================================================

def generate_quiz(
    topic_or_context: str,
    easy: int,
    medium: int,
    hard: int,
    is_rag: bool,
    api_key: str
):

    client = get_groq_client(api_key)

    total_questions = easy + medium + hard

    # --------------------------------------------------------
    # Context instruction
    # --------------------------------------------------------

    if is_rag:

        context_instruction = """
You are an expert academic examiner.

Create a multiple-choice quiz STRICTLY from the provided
educational material.

Use the provided material as the primary source.

Do not introduce information that contradicts the
provided material.

Do not create questions about information that is not
reasonably supported by the provided material.
"""

    else:

        context_instruction = """
You are an expert academic examiner.

Create a high-quality educational multiple-choice quiz
based on the requested topic and your general knowledge.
"""


    # --------------------------------------------------------
    # System prompt
    # --------------------------------------------------------

    system_prompt = f"""
{context_instruction}

IMPORTANT QUIZ RULES:

1. Generate exactly {total_questions} questions.

2. Difficulty distribution MUST be:

   Easy:
   exactly {easy}

   Medium:
   exactly {medium}

   Hard:
   exactly {hard}

3. Every question MUST contain exactly 5 options.

4. There MUST be exactly ONE correct answer.

5. The "correct_answer" field MUST exactly match
   one of the five options.

6. Every question MUST contain an explanation.

7. Every question MUST contain one of these difficulty
   values:

   Easy
   Medium
   Hard

8. Do NOT create duplicate questions.

9. Avoid ambiguous questions.

10. Questions should test understanding rather than
    simply repeating the same sentence from the material.

11. Keep all five options relevant to the question.

12. The correct answer should not always appear in
    the same option position.

13. Return ONLY valid JSON matching the provided schema.
"""


    # --------------------------------------------------------
    # User prompt
    # --------------------------------------------------------

    user_prompt = f"""
Generate the quiz using the following educational material:

============================================================
EDUCATIONAL MATERIAL
============================================================

{topic_or_context}

============================================================
QUIZ REQUIREMENTS
============================================================

Easy questions: {easy}

Medium questions: {medium}

Hard questions: {hard}

Total questions: {total_questions}

Generate exactly the requested number of questions.
"""


    # --------------------------------------------------------
    # Call Groq
    # --------------------------------------------------------

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },

            {
                "role": "user",
                "content": user_prompt
            }
        ],

        temperature=0.7,

        response_format={
            "type": "json_schema",

            "json_schema": {
                "name": "full_quiz",

                "strict": True,

                "schema": QUIZ_JSON_SCHEMA
            }
        }
    )


    # --------------------------------------------------------
    # Get response
    # --------------------------------------------------------

    content = response.choices[0].message.content


    if not content:

        raise ValueError(
            "Groq returned an empty response."
        )


    # --------------------------------------------------------
    # Parse JSON
    # --------------------------------------------------------

    try:

        quiz_data = json.loads(content)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Groq returned invalid JSON: {e}"
        )


    # --------------------------------------------------------
    # Validate using Pydantic
    # --------------------------------------------------------

    try:

        quiz = FullQuiz.model_validate(
            quiz_data
        )

    except Exception as e:

        raise ValueError(
            f"Generated quiz failed validation: {e}"
        )


    # --------------------------------------------------------
    # Validate question count
    # --------------------------------------------------------

    if len(quiz.questions) != total_questions:

        raise ValueError(
            f"Expected {total_questions} questions, "
            f"but Groq generated {len(quiz.questions)}."
        )


    # --------------------------------------------------------
    # Validate every question
    # --------------------------------------------------------

    easy_generated = 0
    medium_generated = 0
    hard_generated = 0


    for question in quiz.questions:

        # ----------------------------------------------------
        # Validate option count
        # ----------------------------------------------------

        if len(question.options) != 5:

            raise ValueError(
                "A generated question does not contain "
                "exactly 5 options."
            )


        # ----------------------------------------------------
        # Validate correct answer
        # ----------------------------------------------------

        if question.correct_answer not in question.options:

            raise ValueError(
                "Correct answer does not match any "
                "of the generated options."
            )


        # ----------------------------------------------------
        # Validate difficulty
        # ----------------------------------------------------

        if question.difficulty not in [
            "Easy",
            "Medium",
            "Hard"
        ]:

            raise ValueError(
                f"Invalid difficulty: "
                f"{question.difficulty}"
            )


        # ----------------------------------------------------
        # Count difficulty
        # ----------------------------------------------------

        if question.difficulty == "Easy":

            easy_generated += 1

        elif question.difficulty == "Medium":

            medium_generated += 1

        elif question.difficulty == "Hard":

            hard_generated += 1


    # --------------------------------------------------------
    # Validate difficulty distribution
    # --------------------------------------------------------

    if easy_generated != easy:

        raise ValueError(
            f"Expected {easy} Easy questions, "
            f"but generated {easy_generated}."
        )


    if medium_generated != medium:

        raise ValueError(
            f"Expected {medium} Medium questions, "
            f"but generated {medium_generated}."
        )


    if hard_generated != hard:

        raise ValueError(
            f"Expected {hard} Hard questions, "
            f"but generated {hard_generated}."
        )


    return quiz


# ============================================================
# AI COACHING REPORT
# ============================================================

def generate_ai_coaching_report(
    quiz_data,
    user_answers,
    api_key: str
):

    client = get_groq_client(api_key)

    analysis_prompt = ""


    # --------------------------------------------------------
    # Prepare quiz performance information
    # --------------------------------------------------------

    for idx, question in enumerate(
        quiz_data.questions
    ):

        user_answer = user_answers.get(
            idx,
            "Left Blank"
        )


        analysis_prompt += f"""
Question {idx + 1}:
{question.question}

Correct Answer:
{question.correct_answer}

Student Answer:
{user_answer}

Difficulty:
{question.difficulty}

Explanation:
{question.explanation}

----------------------------------------
"""


    # --------------------------------------------------------
    # Coaching system prompt
    # --------------------------------------------------------

    system_prompt = """
You are an expert AI Learning Coach.

Analyze the student's quiz performance.

Provide:

1. Overall performance summary
2. Strong areas
3. Weak areas
4. Topics that should be revised
5. Recommended study strategy
6. Suggestions for improving future quiz performance

Keep the response concise, educational and encouraging.

Base your analysis only on the provided quiz
performance information.

Do not invent information that is not supported
by the quiz results.
"""


    # --------------------------------------------------------
    # Call Groq
    # --------------------------------------------------------

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": system_prompt
            },

            {
                "role": "user",
                "content": (
                    "Here is the student's quiz "
                    "performance:\n\n"
                    + analysis_prompt
                )
            }
        ],

        temperature=0.6
    )


    # --------------------------------------------------------
    # Get response
    # --------------------------------------------------------

    content = response.choices[0].message.content


    if not content:

        return (
            "Unable to generate the AI coaching report."
        )


    return content


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_text_from_pdf(
    uploaded_file,
    max_pages: int = 10
) -> str:

    reader = PdfReader(
        uploaded_file
    )


    total_pages = len(
        reader.pages
    )


    # --------------------------------------------------------
    # Page limit
    # --------------------------------------------------------

    if total_pages > max_pages:

        raise ValueError(
            f"PDF too long! Maximum allowed is "
            f"{max_pages} pages. "
            f"Your file has {total_pages} pages."
        )


    # --------------------------------------------------------
    # Extract text
    # --------------------------------------------------------

    text_content = []


    for page in reader.pages:

        page_text = page.extract_text()


        if page_text:

            text_content.append(
                page_text
            )


    # --------------------------------------------------------
    # Check whether text was extracted
    # --------------------------------------------------------

    extracted_text = "\n".join(
        text_content
    ).strip()


    if not extracted_text:

        raise ValueError(
            "No readable text could be extracted "
            "from this PDF. It may be a scanned/image-only PDF."
        )


    return extracted_text