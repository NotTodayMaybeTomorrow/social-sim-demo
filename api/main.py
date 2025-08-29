# main.py
import os
from fastapi import FastAPI, BackgroundTasks, Request
import uvicorn
from generate_comments import generate_comments, save_comments_safely
from data_collector import collect_data
from typing import Dict, Any

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/generate_comments")
async def generate_comments_webhook(request: Request):
    """
    Webhook endpoint that triggers comment generation when a new submission is added to Supabase.
    """
    try:
        payload = await request.json()  # Extract the JSON payload from the request

        # Extract submission ID from the payload
        submission_id = payload.get("record", {}).get("id")

        if not submission_id:
            return {"message": "Error: Submission ID not found in webhook payload"}, 400

        # Run the data collection and comment generation in the background
        background_tasks = BackgroundTasks()
        background_tasks.add_task(process_submission, submission_id)

        return {"message": "Comment generation started in the background", "submission_id": submission_id}, 202  # Accepted

    except Exception as e:
        return {"message": f"Error processing webhook: {str(e)}"}, 500

async def process_submission(submission_id: str):
    """
    Processes a new submission by collecting data, generating personas, and generating comments.
    """
    try:
        final_data = collect_data() #Removed submission_id, collect_data now gets latest
        #TODO: Implement logic that collects only for a specific submission ID
        #final_data = collect_data(submission_id=submission_id)
        if final_data:
            generated_comments, _ = generate_comments() #Removed submission_id since that now happens in collect_data
            save_comments_safely(generated_comments)
        else:
            print("No data collected, skipping comment generation.")
    except Exception as e:
        print(f"Error in background task: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)