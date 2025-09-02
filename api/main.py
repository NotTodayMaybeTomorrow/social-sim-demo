import json
import time
from typing import List, Dict, Any, Tuple
from supabase import create_client, Client
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import your custom modules
from data_collector import get_latest_submission, collect_data
from persona_generator import create_personas_from_data
from generate_comments import generate_comment_with_retry, save_comments_safely, print_results, save_personas_safely
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)

# --- Initialize Supabase and Gemini ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
genai.configure(api_key=GEMINI_API_KEY)
# Note: You might want to instantiate the Gemini model globally if it's used in multiple endpoints,
# but for this specific setup, we'll keep it within the generation function.

# --- FastAPI App Setup ---
app = FastAPI(
    title="Social Media Comment Generator API",
    description="API to generate synthetic comments based on Reddit data and personas.",
    version="1.0.0",
)

# --- Pydantic Models (for request/response validation if needed) ---
# If you plan to have endpoints that accept data, you'll define Pydantic models.
# For now, our main endpoint just triggers a process.

class GenerationResponse(BaseModel):
    message: str
    generated_comments_count: int
    personas_generated_count: int
    success: bool

class Persona(BaseModel):
    persona_id: str
    author: str
    interests: List[str]
    personality_traits: List[str]
    likely_demographics: str
    generated_from_comments: str # Optional: include if you want to return this

class Comment(BaseModel):
    submission_id: int
    author: str
    content: str

# --- API Endpoints ---

@app.get("/")
async def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"message": "Welcome to the Social Media Comment Generator API!"}

@app.post("/generate-comments", response_model=GenerationResponse)
async def generate_and_save_comments():
    """
    Triggers the process of fetching Reddit data, generating personas,
    and creating synthetic comments.
    """
    print("Starting comment generation process...")
    start_time = time.time()

    # Step 1: Get latest submission
    latest_submission = get_latest_submission()
    if not latest_submission:
        print("[generate_comments] No submissions found")
        return GenerationResponse(
            message="Error: No submissions found in the database.",
            generated_comments_count=0,
            personas_generated_count=0,
            success=False
        )

    # Step 2: Collect Reddit data
    reddit_data = collect_data()
    if not reddit_data:
        print("[generate_comments] No Reddit data collected")
        return GenerationResponse(
            message="Error: Could not collect Reddit data.",
            generated_comments_count=0,
            personas_generated_count=0,
            success=False
        )

    # Step 3: Generate personas
    personas = create_personas_from_data(reddit_data)
    if not personas:
        print("[generate_comments] No personas generated")
        return GenerationResponse(
            message="Error: No personas could be generated from the collected data.",
            generated_comments_count=0,
            personas_generated_count=0,
            success=False
        )

    # Save personas to backup file (this function is defined in generate_comments.py)
    save_personas_safely(personas)
    print(f"Generated {len(personas)} personas.")

    # Step 4: Gemini generates comments
    generated_comments = []
    total_personas = len(personas)
    print(f"Generating comments for {total_personas} personas...")

    for i, persona in enumerate(personas, 1):
        print(f"Processing persona {i}/{total_personas}: {persona.get('persona_id', 'N/A')}")
        comment_data = generate_comment_with_retry(persona, latest_submission)

        if comment_data:
            generated_comments.append(comment_data)
            print(f"   ✅ Generated comment by {comment_data.get('author', 'Unknown')}")
        else:
            print(f"   ❌ Failed to generate comment for persona {persona.get('persona_id', 'N/A')}")

    print(f"\nSuccessfully generated {len(generated_comments)} out of {total_personas} comments.")

    # Step 5: Save comments to Supabase
    save_success = save_comments_safely(generated_comments)

    end_time = time.time()
    duration = end_time - start_time
    print(f"Comment generation process finished in {duration:.2f} seconds.")

    return GenerationResponse(
        message=f"Comment generation process completed in {duration:.2f} seconds.",
        generated_comments_count=len(generated_comments),
        personas_generated_count=len(personas),
        success=save_success
    )

# Optional: Add an endpoint to view generated comments or personas
# For simplicity, we'll rely on direct database access for now, but you could
# add endpoints like:
# @app.get("/comments", response_model=List[Comment])
# async def get_comments(): ...
# @app.get("/personas", response_model=List[Persona])
# async def get_personas(): ...

# --- To run locally for testing ---
# You would typically use uvicorn:
# uvicorn main:app --reload