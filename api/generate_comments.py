# generate_comments.py
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
    Full pipeline:
    - Get latest submission from Supabase
    - Collect Reddit data
    - Generate personas (one per author)
    - Generate 1 synthetic comment per author persona
    - Save to Supabase
    """

    # Step 1: get latest submission
    latest_submission = get_latest_submission()
    if not latest_submission:
        print("No submissions found in database")
        return []

    # Step 2: collect Reddit data
    data = collect_data()
    if not data:
        print("No Reddit data collected")
        return []

    # Step 3: generate personas (1 per author)
    personas = create_personas_from_data(data)
    if not personas:
        print("No personas generated")
        return []

    # Step 4: generate comments per persona/author
    generated_comments = []
    for persona in personas:
        author_name = persona.get("author", "unknown_author")

        prompt = (
            f"You are role-playing as this Reddit user persona:\n\n"
            f"Interests: {persona['interests']}\n"
            f"Personality Traits: {persona['personality_traits']}\n"
            f"Demographics: {persona['likely_demographics']}\n\n"
            f"Now, write a single authentic Reddit-style comment "
            f"replying to this post:\n\n"
            f"Title: {latest_submission['title']}\n"
            f"Content: {latest_submission['content']}\n\n"
            f"Do not explain or break character. Just write the comment."
        )

        try:
            response = client.chat.completions.create(
                model=GPT_OSS_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
            )

            comment_text = response.choices[0].message.content.strip()

            generated_comments.append(
                {
                    "author": author_name,
                    "persona_id": persona["persona_id"],
                    "persona_summary": {
                        "interests": persona["interests"],
                        "personality_traits": persona["personality_traits"],
                        "likely_demographics": persona["likely_demographics"],
                    },
                    "generated_comment": comment_text,
                }
            )

        except Exception as e:
            print(f"LLM comment generation failed for {persona['persona_id']}: {e}")

    # Step 5: save into Supabase table
    if generated_comments:
        supabase.table("generated_comments").insert(generated_comments).execute()

    return generated_comments


if __name__ == "__main__":
    results = generate_comments()
    print("Generated comments:")
    for r in results:
        print(f"- {r['author']} ({r['persona_id']}): {r['generated_comment']}")