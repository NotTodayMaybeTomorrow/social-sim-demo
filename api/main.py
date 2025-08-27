# # main.py
# from fastapi import FastAPI, BackgroundTasks
# from typing import List, Dict, Any
# from generate_comments import generate_comments

# app = FastAPI(title="Reddit Persona Comment Generator")

# def run_generation_workflow():
#     """Wrapper function to run the main script."""
#     print("🚀 Starting background task to generate comments...")
#     generate_comments()
#     print("✅ Background task finished.")

# @app.get("/")
# def root():
#     return {"message": "API is running. Use the /generate-comments endpoint to trigger the workflow."}

# @app.post("/generate-comments")
# def generate_comments_endpoint(background_tasks: BackgroundTasks) -> Dict[str, str]:
#     """
#     Accepts a webhook request and starts the comment generation 
#     process in the background.
#     """
#     background_tasks.add_task(run_generation_workflow)
#     return {"message": "Accepted: Comment generation process started in the background."}

import os
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/generate-comments")
def generate_comments_webhook(payload: dict):
    # 這裡才執行 collect_data / generate_comments
    # 確保只在 webhook 被觸發時才跑
    # payload 會包含 Supabase webhook 的資料
    submission_id = payload.get("record", {}).get("id")

    # TODO: 呼叫你的 collect_data() / persona_generator() / insert_to_comments()
    # example:
    # final_data = collect_data(submission_id=submission_id)
    # save_to_comments(final_data)

    return {"message": "comments generated", "submission_id": submission_id}


if __name__ == "__main__":
    # Render 會自動提供 $PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
