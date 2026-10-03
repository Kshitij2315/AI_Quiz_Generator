from typing import List
from pydantic import BaseModel, Field
from pypdf import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

class QuizQuestion(BaseModel):
    question: str = Field(description="The multiple-choice question text.")
    options: List[str] = Field(description="Exactly 5 multiple-choice options.")
    correct_answer: str = Field(description="The exact string of the correct option matching one of the options.")
    explanation: str = Field(description="A detailed explanation of why the answer is correct and others are false.")
    difficulty: str = Field(description="The difficulty tier of this specific question: 'Easy', 'Medium', or 'Hard'.")

class FullQuiz(BaseModel):
    quiz_title: str = Field(description="A catchy, academic title for the generated quiz.")
    questions: List[QuizQuestion] = Field(description="The list of generated quiz questions matching requested distribution.")

def generate_quiz(topic_or_context: str, easy: int, medium: int, hard: int, is_rag: bool):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
    structured_llm = llm.with_structured_output(FullQuiz)

    context_instruction = (
        "You are an elite academic examiner. Create a comprehensive multiple-choice quiz strictly based ON THE PROVIDED PDF TEXT CONTENT.\n"
        "Do not use outside knowledge if it contradicts the text." if is_rag 
        else "You are an elite academic examiner. Create a comprehensive multiple-choice quiz based on general knowledge of the requested topic."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"{context_instruction}\nStrictly provide exactly 5 distinct options per question. Ensure exactly one option is correct. Tag each question with its real difficulty." ),
        ("human", (
            "Generate a customized quiz. Target material/topic: {source}\n"
            "The quiz MUST contain exactly:\n"
            "- {easy_count} 'Easy' questions\n"
            "- {medium_count} 'Medium' questions\n"
            "- {hard_count} 'Hard' questions\n"
            "Total questions: {total_count}. Output must follow the structure."
        ))
    ])
    
    chain = prompt | structured_llm
    
    response = chain.invoke({
        "source": topic_or_context,
        "easy_count": easy,
        "medium_count": medium,
        "hard_count": hard,
        "total_count": easy + medium + hard
    })
    return response

def generate_ai_coaching_report(quiz_data, user_answers):
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)
    
    analysis_prompt = ""
    for idx, q in enumerate(quiz_data.questions):
        user_ans = user_answers.get(idx, "Left Blank")
        analysis_prompt += f"Question " + str(idx+1) + f": {q.question}\nCorrect Answer: {q.correct_answer}\nUser's Answer: {user_ans}\nDifficulty: {q.difficulty}\n---\n"
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an empathetic, expert AI Learning Coach. Analyze the student's test performance, spot technical gaps, and provide actionable, brief study advice. Speak English."),
        ("human", "Here are the details of the completed quiz:\n\n{details}\n\nPlease prepare a personalized analytical performance report and development suggestions for the student.")
    ])
    
    chain = prompt | llm
    return chain.invoke({"details": analysis_prompt}).content

def extract_text_from_pdf(uploaded_file, max_pages: int = 10) -> str:
    reader = PdfReader(uploaded_file)
    total_pages = len(reader.pages)

    if total_pages > max_pages:
        raise ValueError(f"PDF too long! Maximum allowed is {max_pages} pages. Your file has {total_pages} pages.")
    
    text_content = [page.extract_text() for page in reader.pages]
    return "\n".join(text_content)