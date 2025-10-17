# PDF Question Generator (FastAPI)

A FastAPI service that generates questions and answers from uploaded PDFs. After uploading a PDF, the service can produce:
- Multiple Choice Questions (MCQ) with options and correct answer
- Short answer questions with model answers
- Fill-in-the-blank questions with answers

This project is designed for educators, content creators, and quiz builders who want automated question generation from documents.

## Features

- Upload PDF and extract text
- Generate MCQs, short-answer, and fill-in-the-blank questions
- Return structured JSON responses with questions, options, and answers
- Pluggable backend for NLP/LLM-based generation (mock or real LLM)
- REST API with OpenAPI docs (Swagger UI)

## Requirements

- Python 3.10+
- pip
- Windows (development instructions use Windows Shell/PowerShell)

## Installation (Windows)

1. Clone the repo:
   git clone <repo-url>
2. Create & activate virtual environment:
   python -m venv .venv
   .venv\Scripts\activate
3. Install dependencies:
   pip install -r requirements.txt

## Configuration

Configure via environment variables (create a .env for local development):
- APP_HOST (default: 127.0.0.1)
- APP_PORT (default: 8000)
- LOG_LEVEL (default: info)
- GENERATOR_BACKEND (e.g., mock, local, openai)
- OPENAI_API_KEY (if using OpenAI backend)

## Running the app (development)

Start with uvicorn:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Open API docs:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## HTTP API (examples)
/generate-quiz

response as a VALID JSON:
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


## Testing

Run tests with pytest:
pytest

Add unit tests for:
- PDF upload and text extraction
- Each question generator module
- End-to-end API flow



