import json
import time
from typing import List, Dict, Any, Tuple
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
                "persona_id": persona["persona_id"],  # Link comment to persona (for local tracking only)
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
        # First, save to backup file (with persona_id for reference)
        with open("generated_comments_backup.json", "w") as f:
            json.dump(generated_comments, f, indent=2)
        print(f"💾 Backup saved: generated_comments_backup.json")
        
        # Remove persona_id before saving to database (not in schema)
        db_comments = []
        for comment in generated_comments:
            db_comment = {
                "submission_id": comment["submission_id"],
                "author": comment["author"],
                "content": comment["content"]
            }
            db_comments.append(db_comment)
        
        # Try to insert into database
        result = supabase.table("comments").insert(db_comments).execute()
        print(f"✅ Successfully saved {len(db_comments)} comments to database")
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
            
        print(f"📄 Comments available in: generated_comments_backup.json")
        return False


def save_personas_safely(personas: List[Dict[str, Any]]) -> bool:
    """Save personas to a backup file"""
    if not personas:
        print("No personas to save")
        return False
    
    try:
        with open("generated_personas_backup.json", "w") as f:
            json.dump(personas, f, indent=2)
        print(f"💾 Personas backup saved: generated_personas_backup.json")
        return True
    except Exception as e:
        print(f"❌ Error saving personas: {e}")
        return False


def generate_comments() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Pipeline:
    - Get latest submission from Supabase
    - Collect Reddit data
    - Generate personas (one per author)
    - Generate 1 synthetic comment per persona/author
    - Save into Supabase 'comments' table
    
    Returns:
        Tuple of (generated_comments, personas)
    """
    # Step 1: latest submission
    latest_submission = get_latest_submission()
    if not latest_submission:
        print("[generate_comments] No submissions found")
        return [], []

    # Step 2: collect Reddit data
    data = collect_data()
    if not data:
        print("[generate_comments] No Reddit data collected")
        return [], []

    # Step 3: generate personas
    personas = create_personas_from_data(data)
    if not personas:
        print("[generate_comments] No personas generated")
        return [], []

    # Save personas to backup file
    save_personas_safely(personas)

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

    return generated_comments, personas


def print_results(generated_comments: List[Dict[str, Any]], personas: List[Dict[str, Any]]):
    """Print formatted results showing both personas and their comments"""
    print("\n" + "="*80)
    print("GENERATED PERSONAS AND COMMENTS")
    print("="*80)
    
    # Create a mapping of persona_id to persona for easy lookup
    persona_map = {persona['persona_id']: persona for persona in personas}
    
    for comment in generated_comments:
        persona_id = comment.get('persona_id')
        persona = persona_map.get(persona_id, {})
        
        print(f"\n🎭 PERSONA: {persona_id}")
        print(f"   Original Author: {persona.get('author', 'Unknown')}")
        print(f"   Interests: {', '.join(persona.get('interests', []))}")
        print(f"   Personality: {', '.join(persona.get('personality_traits', []))}")
        print(f"   Demographics: {persona.get('likely_demographics', 'N/A')}")
        
        print(f"\n💬 GENERATED COMMENT:")
        print(f"   Author: {comment['author']}")
        print(f"   Content: {comment['content']}")
        print("-" * 80)
    
    # Also print personas that didn't generate comments
    comment_persona_ids = {comment.get('persona_id') for comment in generated_comments}
    unused_personas = [p for p in personas if p['persona_id'] not in comment_persona_ids]
    
    if unused_personas:
        print(f"\n⚠️  PERSONAS WITHOUT COMMENTS ({len(unused_personas)}):")
        for persona in unused_personas:
            print(f"   - {persona['persona_id']} (Author: {persona.get('author', 'Unknown')})")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Total Personas Generated: {len(personas)}")
    print(f"   Total Comments Generated: {len(generated_comments)}")
    print(f"   Success Rate: {len(generated_comments)/len(personas)*100:.1f}%" if personas else "0%")


if __name__ == "__main__":
    generated_comments, personas = generate_comments()
    
    if generated_comments or personas:
        print_results(generated_comments, personas)
        
        # Also save combined results to a single file
        combined_results = {
            "personas": personas,
            "comments": generated_comments,
            "summary": {
                "total_personas": len(personas),
                "total_comments": len(generated_comments),
                "success_rate": len(generated_comments)/len(personas)*100 if personas else 0
            }
        }
        
        with open("combined_results.json", "w") as f:
            json.dump(combined_results, f, indent=2)
        print(f"\n💾 Combined results saved to: combined_results.json")
    else:
        print("No results to display.")