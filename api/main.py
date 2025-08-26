# main.py
from fastapi import FastAPI, BackgroundTasks
from typing import List, Dict, Any
from generate_comments import generate_comments

app = FastAPI(title="Reddit Persona Comment Generator")

def run_generation_workflow():
    """Wrapper function to run the main script."""
    print("🚀 Starting background task to generate comments...")
    generate_comments()
    print("✅ Background task finished.")

@app.get("/")
def root():
    return {"message": "API is running. Use the /generate-comments endpoint to trigger the workflow."}

@app.post("/generate-comments")
def generate_comments_endpoint(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Accepts a webhook request and starts the comment generation 
    process in the background.
    """
    background_tasks.add_task(run_generation_workflow)
    return {"message": "Accepted: Comment generation process started in the background."}