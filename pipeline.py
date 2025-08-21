import os
import praw
from supabase import create_client, Client
from bertopic import BERTopic
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from sentence_transformers import SentenceTransformer

# ===Setup Supabase client===
SUPABASE_URL: str = 'https://wfwrdegsjjqlxskvnlgb.supabase.co'
SUPABASE_ANON_KEY: str = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indmd3JkZWdzampxbHhza3ZubGdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ5Nzg0NzIsImV4cCI6MjA3MDU1NDQ3Mn0.30ABDqOfCH9KnITUVjkT75XULgDFpaSyOo_tNi-Mxzk'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ===Setup PRAW client===
reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="YOUR_USER_AGENT"
)

# ===Initialize SentenceTransformer===
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_latest_submission():
    """Get the most recent submission from Supabase"""
    response = (
        supabase.table("submissions")
        .select("subreddit, submission_flair, is_nsfw, title, content")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    
    if response.data:
        return response.data[0]
    return None

def fetch_reddit_posts(subreddit_name, 
                       submission_flair=None, 
                       is_nsfw=False, 
                       limit=100):
    subreddit_name = subreddit_name.replace('r/','')

    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = []
        
        for submission in subreddit.top(limit=limit):
            # Filter by NSFW status
            if submission.over_18 != is_nsfw:
                continue
                
            # Filter by submission flair if specified
            if submission_flair and submission.link_flair_text != submission_flair:
                continue
            
            posts.append({
                'title': submission.title,
                'content': submission.selftext if submission.selftext else submission.title,
                'url': submission.url,
                'nsfw': submission.over_18,
                'id': submission.id
            })
    
        return posts
    
    except Exception as e:
        print(f"Error fetching posts from r/{subreddit_name}: {e}")
        return []

def find_similar_posts(target_post, reddit_posts, top_k=10):
    """Find most similar posts using sentence embeddings"""
    if not reddit_posts:
        return []
    
    # Combine title and content for target post
    target_text = f"{target_post['title']} {target_post['content']}"
    
    # Combine title and content for Reddit posts
    reddit_texts = [f"{post['title']} {post['content']}" for post in reddit_posts]
    
    # Generate embeddings
    target_embedding = model.encode([target_text])
    reddit_embeddings = model.encode(reddit_texts)
    
    # Calculate cosine similarity
    similarities = cosine_similarity(target_embedding, reddit_embeddings)[0]
    
    # Get top k most similar posts
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    similar_posts = []
    for idx in top_indices:
        post = reddit_posts[idx].copy()
        post['similarity_score'] = similarities[idx]
        similar_posts.append(post)
    
    return similar_posts

def main():
    # Get latest submission from Supabase
    latest_submission = get_latest_submission()
    
    if not latest_submission:
        print("No submissions found in database")
        return
    
    print(f"Latest submission: {latest_submission['title']}")
    print(f"Subreddit: {latest_submission['subreddit']}")
    print(f"Flair: {latest_submission['submission_flair']}")
    print(f"NSFW: {latest_submission['is_nsfw']}")
    print("-" * 50)
    
    # Fetch Reddit posts with filtering
    reddit_posts = fetch_reddit_posts(
        subreddit_name=latest_submission['subreddit'],
        submission_flair=latest_submission['submission_flair'],
        is_nsfw=latest_submission['is_nsfw'],
        limit=200  # Fetch more to have better selection after filtering
    )
    
    print(f"Found {len(reddit_posts)} matching Reddit posts")
    
    if not reddit_posts:
        print("No matching posts found on Reddit")
        return
    
    # Find top 10 most similar posts
    similar_posts = find_similar_posts(latest_submission, reddit_posts, top_k=10)
    
    print("\nTop 10 most similar posts:")
    print("=" * 50)
    
    for i, post in enumerate(similar_posts, 1):
        print(f"{i}. Title: {post['title'][:80]}...")
        print(f"   Score: {post['score']} | Similarity: {post['similarity_score']:.3f}")
        print(f"   Flair: {post['flair']} | NSFW: {post['nsfw']}")
        print(f"   URL: {post['url']}")
        print("-" * 40)

if __name__ == "__main__":
    main()