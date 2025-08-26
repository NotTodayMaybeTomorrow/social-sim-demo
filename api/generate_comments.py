import json
import time
from typing import List, Dict, Any
from supabase import create_client, Client
import google.generativeai as genai

from data_collector import get_latest_submission, collect_data
from persona_generator import create_personas_from_data
from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_NAME,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)

# Init Supabase + Gemini
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_NAME)


def generate_comment_with_retry(persona: Dict[str, Any], latest_submission: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
    """Generate a comment with retry logic and rate limiting"""
    # Truncate submission content to save tokens
    title = latest_submission['title'][:100] if len(latest_submission['title']) > 100 else latest_submission['title']
    content = latest_submission['content'][:200] if len(latest_submission.get('content', '')) > 200 else latest_submission.get('content', '')
    
    prompt = (
        f"Role-play as: {persona['interests'][:2]}, {persona['personality_traits'][:2]}\n\n"
        f"Write Reddit comment for:\n"
        f"Title: {title}\n"
        f"Content: {content}\n\n"
        f"JSON only: {{\"author\": \"username\", \"content\": \"comment\"}}"
    )
    
    for attempt in range(max_retries):
        try:
            # Rate limiting: wait between requests
            if attempt > 0:
                print(f"   Retry attempt {attempt + 1} for persona {persona['persona_id']}")
            
            time.sleep(4.5)  # Wait 4.5 seconds between requests (13 requests/minute max)
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean the response text to extract JSON
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            comment_obj = json.loads(response_text)
            
            return {
                "submission_id": latest_submission["id"],
                "author": comment_obj["author"],
                "content": comment_obj["content"],
            }
            
        except json.JSONDecodeError as e:
            print(f"   JSON decode error for persona {persona['persona_id']} (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"   Response text: {response_text}")
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                # Rate limit hit - wait longer
                wait_time = 30 + (attempt * 10)  # Exponential backoff
                print(f"   Rate limit hit for persona {persona['persona_id']}. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"   Error for persona {persona['persona_id']} (attempt {attempt + 1}): {e}")
                
        if attempt < max_retries - 1:
            time.sleep(2)  # Short wait between retries
    
    print(f"   Failed to generate comment for persona {persona['persona_id']} after {max_retries} attempts")
    return None


def save_comments_safely(generated_comments: List[Dict[str, Any]]) -> bool:
    """Save comments to database with better error handling"""
    if not generated_comments:
        print("No comments to save")
        return False
    
    try:
        # First, save to backup file
        with open("generated_comments_backup.json", "w") as f:
            json.dump(generated_comments, f, indent=2)
        print(f"💾 Backup saved: generated_comments_backup.json")
        
        # Try to insert into database
        result = supabase.table("comments").insert(generated_comments).execute()
        print(f"✅ Successfully saved {len(generated_comments)} comments to database")
        return True
        
    except Exception as e:
        error_msg = str(e)
        
        if "duplicate key" in error_msg or "23505" in error_msg:
            print("❌ Database error: Duplicate key constraint")
            print("💡 Solutions:")
            print("   1. Clear existing comments: DELETE FROM comments;")
            print("   2. Or check your database schema")
            print(f"   3. Comments saved in backup file: generated_comments_backup.json")
            
        elif "foreign key" in error_msg:
            print("❌ Database error: Foreign key constraint")
            print("💡 Make sure the submission_id exists in submissions table")
            
        else:
            print(f"❌ Database error: {e}")
            
        print(f"📁 Comments available in: generated_comments_backup.json")
        return False


def generate_comments() -> List[Dict[str, Any]]:
    """
    Pipeline:
    - Get latest submission from Supabase
    - Collect Reddit data
    - Generate personas (one per author)
    - Generate 1 synthetic comment per persona/author
    - Save into Supabase 'comments' table
    """
    # Step 1: latest submission
    latest_submission = get_latest_submission()
    if not latest_submission:
        print("[generate_comments] No submissions found")
        return []

    # Step 2: collect Reddit data
    data = collect_data()
    if not data:
        print("[generate_comments] No Reddit data collected")
        return []

    # Step 3: generate personas
    personas = create_personas_from_data(data)
    if not personas:
        print("[generate_comments] No personas generated")
        return []

    # Step 4: Gemini generates 1 comment per persona/author with rate limiting
    generated_comments = []
    total_personas = len(personas)
    
    print(f"Generating comments for {total_personas} personas (with rate limiting)...")
    print("This will take approximately {:.1f} minutes due to API rate limits.".format(total_personas * 4.5 / 60))
    
    for i, persona in enumerate(personas, 1):
        print(f"Processing persona {i}/{total_personas}: {persona['persona_id']}")
        
        comment_data = generate_comment_with_retry(persona, latest_submission)
        
        if comment_data:
            generated_comments.append(comment_data)
            print(f"   ✅ Generated comment by {comment_data['author']}")
        else:
            print(f"   ❌ Skipped persona {persona['persona_id']}")
    
    print(f"\nSuccessfully generated {len(generated_comments)} out of {total_personas} comments.")

    # Step 5: save into Supabase "comments" table with better error handling
    save_comments_safely(generated_comments)

    return generated_comments


if __name__ == "__main__":
    results = generate_comments()
    print("Generated comments:")
    for r in results:
        print(f"- {r['author']}: {r['content']}")