import json
from openai import OpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, GPT_OSS_MODEL_NAME

# Initialize client
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL,
)


def generate_persona(comments_text: str):
    """
    Generates a persona from a block of comments using the LLM.
    Returns a dict or None.
    """
    try:
        system_prompt = (
            "You are an expert at creating user personas from social media comments.\n"
            "Analyze the comments and generate a persona as valid JSON with this structure:\n"
            "{\n"
            "  \"interests\": [\"list\", \"of\", \"interests\"],\n"
            "  \"personality_traits\": [\"list\", \"of\", \"traits\"],\n"
            "  \"likely_demographics\": \"short demographic description\"\n"
            "}"
        )

        response = client.chat.completions.create(
            model=GPT_OSS_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Based on the following comments, generate a persona:\n\n{comments_text}",
                },
            ],
            response_format={"type": "json_object"},
        )

        persona_data = json.loads(response.choices[0].message.content)
        return persona_data

    except Exception as e:
        print(f"[persona_generator] API call failed: {e}")
        return None


def create_personas_from_data(data):
    """
    Build personas from collected Reddit data.
    One persona per unique author (if enough comments).
    """
    all_personas = []
    persona_counter = 1

    for post in data:
        for comment in post.get("top_level_comments", []):
            author_comments = comment.get("author_hot_comments", [])

            if len(author_comments) >= 5:  # require enough comments to build persona
                comments_text = "\n".join([f"- {c['body']}" for c in author_comments])

                print(
                    f"Generating persona {persona_counter} for author '{comment['author']}'..."
                )
                persona = generate_persona(comments_text)

                if persona:
                    persona["persona_id"] = f"persona_{persona_counter}"
                    persona["author"] = comment["author"]  # ✅ include author here
                    persona["generated_from_comments"] = comments_text

                    all_personas.append(persona)
                    persona_counter += 1
                else:
                    print(f"Skipping persona for '{comment['author']}' (API failure).")

                if len(all_personas) >= 100:
                    return all_personas

    return all_personas
