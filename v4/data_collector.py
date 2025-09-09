import os
import json
import praw
import numpy as np
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    REDDIT_POST_LIMIT,
    TOP_SIMILAR_POSTS,
)

# Supabase setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Reddit API setup
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
)

def get_latest_submission() -> Optional[Dict[str, Any]]:
    """Get the most recent submission from Supabase"""
    try:
        response = (
            supabase.table("submissions")
            .select("id, subreddit, submission_flair, is_nsfw, title, content")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )

        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error fetching latest submission: {e}")
        return None


def test_reddit_connection() -> bool:
    """Test if Reddit API credentials are working"""
    try:
        subreddit = reddit.subreddit("python")
        # Try to access a basic property to test connection
        _ = subreddit.display_name
        print("Reddit connection test: Connection succeeded.")
        return True
    except Exception as e:
        print(f"Reddit connection failed: {e}")
        return False


def fetch_reddit_posts(
    subreddit_name: str, 
    submission_flair: Optional[str] = None, 
    is_nsfw: bool = False, 
    limit: int = REDDIT_POST_LIMIT
) -> List[Dict[str, Any]]:
    """Fetch posts from Reddit with filtering"""
    subreddit_name = subreddit_name.replace("r/", "")

    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts = []

        for submission in subreddit.hot(limit=limit):
            # Filter NSFW
            if submission.over_18 != is_nsfw:
                continue

            # Filter flair if specified
            if submission_flair and submission.link_flair_text != submission_flair:
                continue

            posts.append({
                "title": submission.title,
                "content": submission.selftext if submission.selftext else submission.title,
                "url": submission.url,
                "score": submission.score,
                "flair": submission.link_flair_text,
                "nsfw": submission.over_18,
                "id": submission.id,
            })

        return posts
    except Exception as e:
        print(f"Error fetching Reddit posts: {e}")
        return []


def find_similar_posts_embeddings(
    target_post: Dict[str, str], 
    reddit_posts: List[Dict[str, Any]], 
    top_k: int = TOP_SIMILAR_POSTS
) -> List[Dict[str, Any]]:
    """Find most similar posts using SentenceTransformers embeddings + cosine similarity"""
    if not reddit_posts:
        return []

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    try:
        target_text = f"{target_post['title']} {target_post['content']}"
        reddit_texts = [f"{post['title']} {post['content']}" for post in reddit_posts]

        # Encode with sentence transformer
        target_embedding = model.encode([target_text], convert_to_numpy=True, normalize_embeddings=True)
        reddit_embeddings = model.encode(reddit_texts, convert_to_numpy=True, normalize_embeddings=True)

        similarities = cosine_similarity(target_embedding, reddit_embeddings)[0]

        # Get top k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        similar_posts = []
        for idx in top_indices:
            post = reddit_posts[idx].copy()
            post["similarity_score"] = float(similarities[idx])
            similar_posts.append(post)

        return similar_posts
    except Exception as e:
        print(f"Error computing similarities: {e}")
        return []


def fetch_post_comments(post_id: str, max_comments: int = 30) -> List[Dict[str, Any]]:
    """Fetch comments for a specific post"""
    try:
        submission = reddit.submission(id=post_id)
        submission.comment_sort = 'top'
        
        comments = []
        for comment in submission.comments:
            if len(comments) >= max_comments:
                break
            
            if not isinstance(comment, praw.models.MoreComments) and comment.body:
                comment_data = {
                    "score": comment.score,
                    "body": comment.body,
                    "author": comment.author.name if comment.author else "[deleted]",
                    "author_hot_comments": []
                }
                
                # Fetch author's other comments
                if comment.author and comment.author.name != "[deleted]":
                    try:
                        for auth_comment in comment.author.comments.hot(limit=50):
                            if (not isinstance(auth_comment, praw.models.MoreComments) and 
                                auth_comment.body and len(comment_data['author_hot_comments']) < 30):
                                comment_data['author_hot_comments'].append({
                                    "score": auth_comment.score,
                                    "body": auth_comment.body
                                })
                    except Exception as e:
                        print(f"   Error fetching comments for {comment.author.name}: {e}")
                        
                comments.append(comment_data)
        
        return comments
    except Exception as e:
        print(f"   Error fetching comments for post {post_id}: {e}")
        return []


def collect_data() -> Optional[List[Dict[str, Any]]]:
    """Main function to collect and structure all the data."""
    if not test_reddit_connection():
        print("Please check your Reddit API credentials")
        return None

    latest_submission = get_latest_submission()
    if not latest_submission:
        print("No submissions found in database")
        return None

    print(f"Latest submission: {latest_submission['title']}")
    print(f"Subreddit: {latest_submission['subreddit']}")
    print(f"Flair: {latest_submission['submission_flair']}")
    print(f"NSFW: {latest_submission['is_nsfw']}")
    print("-" * 50)

    reddit_posts = fetch_reddit_posts(
        subreddit_name=latest_submission["subreddit"],
        submission_flair=latest_submission["submission_flair"],
        is_nsfw=latest_submission["is_nsfw"],
        limit=REDDIT_POST_LIMIT,
    )

    print(f"Found {len(reddit_posts)} matching Reddit posts")

    if not reddit_posts:
        print("No matching posts found on Reddit")
        return None

    similar_posts = find_similar_posts_embeddings(latest_submission, reddit_posts)

    print(f"\nTop {len(similar_posts)} most similar posts (using Sentence Transformers):")
    print("=" * 50)
    
    final_data = []

    for i, post in enumerate(similar_posts, 1):
        print(f"{i}. Title: {post['title'][:50]}...")
        print(f"   Score: {post['score']} | Similarity: {post['similarity_score']:.3f}")
        print(f"   Flair: {post['flair']} | NSFW: {post['nsfw']}")
        print("-" * 40)
        
        post_data = post.copy()
        post_data['top_level_comments'] = fetch_post_comments(post['id'])
        
        final_data.append(post_data)

    print(f"\nCollected data for {len(final_data)} posts with comments.")
    return final_data


if __name__ == "__main__":
    final_data = collect_data()
    if final_data:
        with open("reddit_data.json", "w") as f:
            json.dump(final_data, f, indent=2)
        print("Data successfully written to reddit_data.json")