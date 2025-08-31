# main.py
import os
from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
from generate_comments import generate_comments, save_comments_safely
from data_collector import collect_data

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.post("/api/generate_comments")
async def generate_comments_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        submission_id = payload.get("record", {}).get("id")

        if not submission_id:
            return {"message": "Error: Submission ID not found in webhook payload"}, 400

        background_tasks.add_task(process_submission, submission_id)
        return {"message": "Comment generation started in the background", "submission_id": submission_id}, 202

    except Exception as e:
        return {"message": f"Error processing webhook: {str(e)}"}, 500

async def process_submission(submission_id: str):
    try:
        #TODO: Change Collect data to only get comments based on a submission ID instead of getting the latest
        final_data = collect_data() #collect_data(submission_id=submission_id)

        if final_data:
            generated_comments, _ = generate_comments() #generate_comments(submission_id=submission_id)
            save_comments_safely(generated_comments)
        else:
            print("No data collected, skipping comment generation.")
    except Exception as e:
        print(f"Error in background task: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)