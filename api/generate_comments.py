import json
from typing import List, Dict, Any
from supabase import create_client, Client
from openai import OpenAI

from data_collector import get_latest_submission, collect_data
from persona_generator import create_personas_from_data
from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    GPT_OSS_MODEL_NAME,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)

# Init Supabase + LLM
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


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

    # Step 4: LLM generates 1 comment per persona/author
    generated_comments = []
    for persona in personas:
        prompt = (
            f"You are role-playing as this Reddit user persona:\n\n"
            f"Interests: {persona['interests']}\n"
            f"Personality Traits: {persona['personality_traits']}\n"
            f"Demographics: {persona['likely_demographics']}\n\n"
            f"Task: Write ONE authentic Reddit comment replying to this post:\n\n"
            f"Title: {latest_submission['title']}\n"
            f"Content: {latest_submission['content']}\n\n"
            f"Return ONLY valid JSON with fields:\n"
            f"{{\"author\": \"fake_reddit_username\", \"content\": \"the comment\"}}"
        )

        try:
            response = client.chat.completions.create(
                model=GPT_OSS_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            comment_obj = json.loads(response.choices[0].message.content)

            generated_comments.append(
                {
                    "submission_id": latest_submission["id"],
                    "author": comment_obj["author"],
                    "content": comment_obj["content"],
                }
            )

        except Exception as e:
            print(
                f"[generate_comments] Failed for persona {persona['persona_id']}: {e}"
            )

    # Step 5: save into Supabase "comments" table
    if generated_comments:
        supabase.table("comments").insert(generated_comments).execute()
        print(f"[generate_comments] Inserted {len(generated_comments)} comments.")

    return generated_comments


if __name__ == "__main__":
    results = generate_comments()
    print("Generated comments:")
    for r in results:
        print(f"- {r['author']}: {r['content']}")
