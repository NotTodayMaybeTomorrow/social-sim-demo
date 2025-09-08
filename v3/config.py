import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Reddit API credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "SocialSimDemo/1.0")

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Gemini API credentials
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# Configuration
MAX_PERSONAS = int(os.getenv("MAX_PERSONAS", "5"))
MIN_COMMENTS_FOR_PERSONA = int(os.getenv("MIN_COMMENTS_FOR_PERSONA", "5"))
REDDIT_POST_LIMIT = int(os.getenv("REDDIT_POST_LIMIT", "200"))
TOP_SIMILAR_POSTS = int(os.getenv("TOP_SIMILAR_POSTS", "10"))

# Validate required environment variables
required_vars = [
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET", 
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "GEMINI_API_KEY"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")