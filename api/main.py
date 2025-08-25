# main.py
from fastapi import FastAPI
from typing import List, Dict, Any
from generate_comments import generate_comments

app = FastAPI(title="Reddit Persona Comment Generator")

@app.get("/")
def root():
    return {"message": "API is running"}

@app.post("/generate-comments")
def generate_comments_endpoint() -> List[Dict[str, Any]]:
    return generate_comments()
