import json
import time
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_NAME)


def generate_persona(comments_text: str, max_retries: int = 3):
    """
    Generates a persona from a block of comments using Gemini with rate limiting.
    OPTIMIZED FOR MINIMAL TOKEN USAGE.
    """
    # Truncate comments to reduce tokens dramatically
    if len(comments_text) > 2000:  # ~500 tokens max
        comments_text = comments_text[:2000] + "..."
    
    # Much shorter prompt to save tokens
    prompt = f"""Create persona from comments. JSON only:

{{"interests": ["hobby1", "hobby2"], "personality_traits": ["trait1", "trait2"], "likely_demographics": "brief desc (<= 50 words)"}}

Comments:
{comments_text}"""

    for attempt in range(max_retries):
        try:
            # Rate limiting: wait between requests
            time.sleep(4.5)  # Wait 4.5 seconds between requests
            
            response = model.generate_content(prompt)
            
            # Clean the response text to extract JSON
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            persona_data = json.loads(response_text)
            return persona_data

        except json.JSONDecodeError as e:
            print(f"   JSON decode error (attempt {attempt + 1}): {e}")
            if attempt == max_retries - 1:
                print(f"   Response text: {response_text}")
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                # Rate limit hit - wait longer
                wait_time = 30 + (attempt * 10)  # Exponential backoff
                print(f"   Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"   API call error (attempt {attempt + 1}): {e}")
                
        if attempt < max_retries - 1:
            time.sleep(2)  # Short wait between retries
    
    print(f"   Failed to generate persona after {max_retries} attempts")
    return None


def create_personas_from_data(data):
    """
    Build personas from collected Reddit data.
    One persona per unique author (if enough comments).
    """
    all_personas = []
    persona_counter = 1

    # Count total eligible authors for time estimation
    eligible_authors = []
    for post in data:
        for comment in post.get("top_level_comments", []):
            author_comments = comment.get("author_hot_comments", [])
            if len(author_comments) >= 5:
                eligible_authors.append(comment['author'])
    
    print(f"Found {len(eligible_authors)} eligible authors for persona generation")
    print("Estimated time: {:.1f} minutes (due to API rate limits)".format(len(eligible_authors) * 4.5 / 60))

    for post in data:
        for comment in post.get("top_level_comments", []):
            author_comments = comment.get("author_hot_comments", [])

            if len(author_comments) >= 5:  # require enough comments to build persona
                # OPTIMIZE: Limit comment data to reduce tokens
                top_comments = sorted(author_comments, key=lambda x: x.get('score', 0), reverse=True)[:3]  # Only top 3 comments
                comments_text = "\n".join([f"- {c['body'][:200]}..." if len(c['body']) > 200 else f"- {c['body']}" for c in top_comments])  # Truncate each comment

                print(f"Generating persona {persona_counter} for author '{comment['author']}'...")
                persona = generate_persona(comments_text)

                if persona:
                    persona["persona_id"] = f"persona_{persona_counter}"
                    persona["author"] = comment["author"]  # ✅ include author here
                    persona["generated_from_comments"] = comments_text

                    all_personas.append(persona)
                    print(f"   ✅ Created persona_{persona_counter}")
                    persona_counter += 1
                else:
                    print(f"   ❌ Skipping persona for '{comment['author']}' (failed to generate)")

                if len(all_personas) >= 5:
                    break
        if len(all_personas) >= 5:
            break

    print(f"\nGenerated {len(all_personas)} personas total")
    return all_personas