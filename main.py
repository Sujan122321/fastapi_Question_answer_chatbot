from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from openai import AzureOpenAI
import PyPDF2
import io
import json
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_MODEL")

# Initialize FastAPI
app = FastAPI(
    title="Quiz Generator with Azure OpenAI",
    description="Generate MCQs, Short Answer, and Fill in the Blanks from PDF"
)

# Pydantic models for response
class MCQQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None

class ShortAnswerQuestion(BaseModel):
    question: str
    expected_answer: str

class FillInTheBlank(BaseModel):
    question: str
    answer: str
    hint: Optional[str] = None

class QuizResponse(BaseModel):
    success: bool
    message: str
    mcq_questions: List[MCQQuestion]
    short_answer_questions: List[ShortAnswerQuestion]
    fill_in_the_blanks: List[FillInTheBlank]
    total_questions: int


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF file"""
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading PDF: {str(e)}")


def generate_questions_with_azure(text: str, num_mcq: int, num_short: int, num_blanks: int) -> Dict:
    """Generate all types of questions using Azure OpenAI"""
    
    prompt = f"""Based on the following text, generate questions in THREE categories:

TEXT:
{text[:8000]}

Generate exactly:
1. {num_mcq} Multiple Choice Questions (MCQ)
2. {num_short} Short Answer Questions
3. {num_blanks} Fill in the Blank Questions

Return your response as a VALID JSON object with this EXACT structure:
{{
  "mcq": [
    {{
      "question": "Question text?",
      "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
      "correct_answer": "A",
      "explanation": "Brief explanation"
    }}
  ],
  "short_answer": [
    {{
      "question": "Question text?",
      "expected_answer": "Expected answer in 2-3 sentences"
    }}
  ],
  "fill_in_the_blanks": [
    {{
      "question": "The capital of France is _____.",
      "answer": "Paris",
      "hint": "A European city"
    }}
  ]
}}

IMPORTANT: Return ONLY valid JSON, no extra text or markdown."""

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": "You are an expert educator who creates high-quality assessment questions. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        
        response_text = response.choices[0].message.content
        
        # Clean response
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse JSON
        questions_data = json.loads(response_text)
        return questions_data
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Azure OpenAI error: {str(e)}")


@app.get("/")
def home():
    return {
        "message": "Quiz Generator API with Azure OpenAI",
        "endpoints": {
            "generate": "POST /generate-quiz",
            "health": "GET /health"
        },
        "features": [
            "Multiple Choice Questions (MCQ)",
            "Short Answer Questions",
            "Fill in the Blanks"
        ]
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "azure_configured": bool(os.getenv("AZURE_OPENAI_API_KEY")),
        "deployment": DEPLOYMENT_NAME
    }


@app.post("/generate-quiz", response_model=QuizResponse)
async def generate_quiz(
    file: UploadFile = File(..., description="PDF file to process"),
    num_mcq: int = Form(5, ge=1, le=10, description="Number of MCQ questions"),
    num_short_answer: int = Form(3, ge=1, le=10, description="Number of short answer questions"),
    num_fill_blanks: int = Form(3, ge=1, le=10, description="Number of fill in the blank questions")
):
    """
    Generate quiz questions from PDF
    
    **Returns JSON with:**
    - Multiple Choice Questions with answers
    - Short Answer Questions with expected answers
    - Fill in the Blank Questions with answers
    """
    
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Read PDF
        pdf_bytes = await file.read()
        
        # Check file size (max 10MB)
        if len(pdf_bytes) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large. Max 10MB")
        
        # Extract text
        text = extract_text_from_pdf(pdf_bytes)
        
        if len(text) < 100:
            raise HTTPException(status_code=400, detail="PDF text too short. Need at least 100 characters")
        
        print(f"Extracted {len(text)} characters from PDF")
        print(f"Generating: {num_mcq} MCQs, {num_short_answer} Short Answer, {num_fill_blanks} Fill Blanks")
        
        # Generate questions
        questions_data = generate_questions_with_azure(text, num_mcq, num_short_answer, num_fill_blanks)
        
        # Parse into models
        mcq_questions = [MCQQuestion(**q) for q in questions_data.get("mcq", [])]
        short_questions = [ShortAnswerQuestion(**q) for q in questions_data.get("short_answer", [])]
        blank_questions = [FillInTheBlank(**q) for q in questions_data.get("fill_in_the_blanks", [])]
        
        total = len(mcq_questions) + len(short_questions) + len(blank_questions)
        
        return QuizResponse(
            success=True,
            message=f"Successfully generated {total} questions from {file.filename}",
            mcq_questions=mcq_questions,
            short_answer_questions=short_questions,
            fill_in_the_blanks=blank_questions,
            total_questions=total
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Quiz Generator with Azure OpenAI")
    print("=" * 60)
    print(f"📍 Server: http://localhost:8000")
    print(f"📖 Docs: http://localhost:8000/docs")
    print(f"🔧 Deployment: {DEPLOYMENT_NAME}")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)