from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import bcrypt
from jose import jwt
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User, Resume, Question
from datetime import datetime, timedelta
import os
import shutil
import pdfplumber
from groq import Groq
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# pwd_context = CryptContext(schemes=["bcrypt"])
SECRET_KEY = "dev-secret-key-change-later"
ALGORITHM = "HS256"
UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
Base.metadata.create_all(bind=engine)


def generative_questions(extracted_text: str) -> list:
    response =client.chat.completions.create(
        model = "llama-3.3-70b-versatile",
        messages = [
            {
                "role": "user",
                "content": f""" 
                  You are an expert interview coach. Based on the resume below, generate 10 relevant questions.
                  Return ONLY a JSON array of objects like this:
                    [
                        {{"question": "Tell me about your experience with...", "category": "Technical"}},
                        {{"question": "Describe a time when...", "category": "Behavioral"}}
                    ]
                     Resume:
                    {extracted_text}

                    """
            }
        ],
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    if isinstance(result, list):
        return result
    
    return result.get("questions", result.get("items", []))


# ── helpers ──────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ── schemas ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str



# ── routes ───────────────────────────────────────────────

# ── Password Hashing Helpers ──────────────────────────────

def get_password_hash(password: str) -> str:
    """Hashes a plain text password using native bcrypt."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a hashed password string."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw =get_password_hash(data.password)
    new_user = User(email=data.email, name=data.name, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email, "name": new_user.name, "message": "User created successfully"}


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.utcnow() + timedelta(days=7)
    token = jwt.encode({"sub": data.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer", "id": user.id, "email": user.email, "name": user.name}


@app.get("/user/data")
def getUserData(id: int, db: Session = Depends(get_db)):
    user = db.query(id).filter(User.id ==  id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    resume_count = db.query(Resume).filter(Resume.user_id == id).count()
    return {
        "name" : user.name,
        "resumeCount": resume_count,
    }





@app.post("/resume/upload")
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_text = extract_text_from_pdf(file_path)

    new_resume = Resume(user_id=1, file_path=file_path, extracted_text=extracted_text)
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)

    questions_data = generative_questions(extracted_text)

    ##save questions to db
    saved_questions = []
    for q in questions_data:
        question = Question(
            resume_id=new_resume.id,
            question_text=q['question'],
            category=q.get("category", "General"),
        )
        db.add(question)
        saved_questions.append({"question": q["question"], "category": q.get("category")})

    db.commit()

    return {
        "resume_id": new_resume.id,
        "message": "Resume uploaded successfully!",
        "questions": saved_questions,
        "extracted_text_preview": extracted_text[:300]
    }