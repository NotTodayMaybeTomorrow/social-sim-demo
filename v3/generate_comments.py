import json
import time
from typing import List, Dict, Any, Tuple
from supabase import create_client, Client
import google.generativeai as genai

from data_collector import get_latest_submission, collect_data
from persona_generator import create_personas_from_reddit_data
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
    title = latest_submission['title'][:100] if len(latest_submission['title']) > 100 else latest_submission['title']
    content = latest_submission.get('content', '')[:200] if len(latest_submission.get('content', '')) > 200 else latest_submission.get('content', '')
    
    prompt = (
        f"Role-play as the persona: {persona['interests'][:2]}, {persona['personality_traits'][:2]}\n\n"
        f"Write a tailored Reddit comment with distinct writing styles based on the persona for:\n"
        f"Title: {title}\n"
        f"Content: {content}\n\n"
        f"JSON only: {{\"author\": \"username\", \"content\": \"comment\"}}"
    )
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"   Retry attempt {attempt + 1} for persona {persona['persona_id']}")
            
            time.sleep(4.5)  # Rate limit
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            comment_obj = json.loads(response_text.strip())
            
            return {
                "submission_id": latest_submission["id"],
                "author": comment_obj["author"],
                "content": comment_obj["content"],
                "persona_id": persona["persona_id"],
            }
            
        except json.JSONDecodeError as e:
            print(f"   JSON decode error for persona {persona['persona_id']} (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"   Response text: {response_text}")
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = 30 + (attempt * 10)
                print(f"   Rate limit hit for persona {persona['persona_id']}. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"   Error for persona {persona['persona_id']} (attempt {attempt + 1}): {e}")
                
        if attempt < max_retries - 1:
            time.sleep(2)
    
    print(f"   Failed to generate comment for persona {persona['persona_id']} after {max_retries} attempts")
    return None


def save_comments_safely(generated_comments: List[Dict[str, Any]]) -> bool:
    """Save comments to database with backup"""
    if not generated_comments:
        print("No comments to save")
        return False
    
    try:
        with open("generated_comments_backup.json", "w") as f:
            json.dump(generated_comments, f, indent=2)
        print(f"💾 Backup saved: generated_comments_backup.json")
        
        db_comments = [
            {
                "submission_id": c["submission_id"],
                "author": c["author"],
                "content": c["content"]
            } for c in generated_comments
        ]
        
        supabase.table("comments").insert(db_comments).execute()
        print(f"✅ Successfully saved {len(db_comments)} comments to database")
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        print(f"📄 Comments available in backup: generated_comments_backup.json")
        return False


def save_personas_safely(personas: List[Dict[str, Any]]) -> bool:
    """Save personas to backup file"""
    if not personas:
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
    - Generate personas (one per cluster)
    - Visualize clusters automatically
    - Generate 1 synthetic comment per persona
    - Save results
    """
    latest_submission = get_latest_submission()
    if not latest_submission:
        print("[generate_comments] No submissions found")
        return [], []

    data = collect_data()
    if not data:
        print("[generate_comments] No Reddit data collected")
        return [], []

    # Generate personas and visualize clusters automatically
    personas = create_personas_from_reddit_data(data, num_clusters=10)
    if not personas:
        print("[generate_comments] No personas generated")
        return [], []

    save_personas_safely(personas)

    generated_comments = []
    total_personas = len(personas)
    
    print(f"Generating comments for {total_personas} personas (with rate limiting)...")
    print("Approximate duration: {:.1f} minutes.".format(total_personas * 4.5 / 60))
    
    for i, persona in enumerate(personas, 1):
        print(f"Processing persona {i}/{total_personas}: {persona['persona_id']}")
        comment_data = generate_comment_with_retry(persona, latest_submission)
        if comment_data:
            generated_comments.append(comment_data)
            print(f"   ✅ Generated comment by {comment_data['author']}")
        else:
            print(f"   ❌ Skipped persona {persona['persona_id']}")

    print(f"\nGenerated {len(generated_comments)} out of {total_personas} comments.")
    save_comments_safely(generated_comments)

    return generated_comments, personas


def print_results(generated_comments: List[Dict[str, Any]], personas: List[Dict[str, Any]]):
    """Display personas and their generated comments"""
    print("\n" + "="*80)
    print("GENERATED PERSONAS AND COMMENTS")
    print("="*80)
    
    persona_map = {p['persona_id']: p for p in personas}
    
    for comment in generated_comments:
        persona = persona_map.get(comment['persona_id'], {})
        print(f"\n🎭 PERSONA: {comment['persona_id']}")
        print(f"   Interests: {', '.join(persona.get('interests', []))}")
        print(f"   Personality: {', '.join(persona.get('personality_traits', []))}")
        print(f"   Demographics: {persona.get('likely_demographics', 'N/A')}")
        print(f"💬 COMMENT ({comment['author']}): {comment['content']}")
        print("-"*80)
    
    comment_ids = {c.get('persona_id') for c in generated_comments}
    unused_personas = [p for p in personas if p['persona_id'] not in comment_ids]
    if unused_personas:
        print(f"\n⚠️  PERSONAS WITHOUT COMMENTS: {len(unused_personas)}")
        for persona in unused_personas:
            print(f"   - {persona['persona_id']}")


if __name__ == "__main__":
    generated_comments, personas = generate_comments()
    
    if generated_comments or personas:
        print_results(generated_comments, personas)
        
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
