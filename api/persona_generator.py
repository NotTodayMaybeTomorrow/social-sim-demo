import json
from openai import OpenAI
from api.config import OPENAI_API_KEY, OPENAI_BASE_URL, GPT_OSS_MODEL_NAME

def generate_persona(comments_text):
    """
    Generates a persona by calling a GPT-OSS model via an OpenAI-compatible API.
    Returns a dictionary with the persona data or None on failure.
    """
    try:
        client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL,
        )

        system_prompt = (
            '''You are an expert in creating user personas from social media comments. Analyze the provided Reddit comments and generate a detailed persona of the author.

                Your output must be a single, valid JSON object with the following schema:
                {
                "interests": ["string", "string", ...],
                "traits": ["string", "string", ...],
                "region": "one of: NA, EU, EAS, SEA, SA, ME, AF, LATAM, OCE",
                "age": "one of: teen, 20s, 30s, 40s, 50+, unknown",
                "gender": "one of: male, female, non-binary, unknown"
                }'''
        )

        response = client.chat.completions.create(
            model=GPT_OSS_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Based on the following comments, generate a persona:\n\nComments:\n{comments_text}"}
            ],
            response_format={"type": "json_object"}
        )

        # The response format is guaranteed to be a JSON object, so no need for manual parsing.
        persona_data = json.loads(response.choices[0].message.content)
        return persona_data
    
    except Exception as e:
        print(f"API call failed: {e}")
        return None


def create_personas_from_data(data):
    """
    Processes the collected data to create a list of personas.
    Each persona is based on one author's set of up to 10 comments.
    """
    all_personas = []
    persona_counter = 1

    for post in data:
        for comment in post.get('top_level_comments', []):
            author_comments = comment.get('author_hot_comments', [])
            
            # We generate a persona only if the author has a sufficient number of comments
            if len(author_comments) >= 5:
                # Combine all comment bodies into a single string for the prompt
                comments_text = "\n".join([f"- {c['body']}" for c in author_comments])

                print(f"Generating persona {len(all_personas) + 1} for author '{comment['author']}'...")
                persona = generate_persona(comments_text)
                
                if persona:
                    # Add a unique ID and the source comments to the persona
                    persona['persona_id'] = f"persona_{persona_counter}"
                    persona['generated_from_comments'] = comments_text
                    all_personas.append(persona)
                    persona_counter += 1
                else:
                    print(f"Skipping persona for '{comment['author']}' due to API failure.")

                # Stop if we reach 100 personas
                if len(all_personas) >= 100:
                    return all_personas
                    
    return all_personas