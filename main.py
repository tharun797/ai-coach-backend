from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from models import User, Resume, Question
from datetime import datetime, timedelta
import os
import shutil
import pdfplumber

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"])
SECRET_KEY = "dev-secret-key-change-later"
ALGORITHM = "HS256"
UPLOAD_DIR = "uploads/resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)

Base.metadata.create_all(bind=engine)


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

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = pwd_context.hash(data.password)
    new_user = User(email=data.email, name=data.name, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"id": new_user.id, "email": new_user.email, "name": new_user.name, "message": "User created successfully"}


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    expire = datetime.utcnow() + timedelta(days=7)
    token = jwt.encode({"sub": data.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer", "id": user.id, "email": user.email, "name": user.name}


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

    return {
        "resume_id": new_resume.id,
        "message": "Resume uploaded successfully!",
        "extracted_text_preview": extracted_text[:300]
    }