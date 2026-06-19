from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session

from database import engine, Base, get_db
from models import User

from datetime import datetime, timedelta

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"])
SECRET_KEY = "dev-secret-key-change-later"
ALGORITHM = "HS256"

Base.metadata.create_all(bind=engine)

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_pw = pwd_context.hash(data.password)
    new_user = {
        "email": data.email,
        "name": data.name,
        "password": hashed_pw,
    }
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message" : "User created successfully"}


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not pwd_context.verify(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    expire = datetime.utcnow() + timedelta(days=7)
    token = jwt.encode(
        {"sub" : data.email, "exp" : expire},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {"access_token": token, "token_type": "bearer"}


 
