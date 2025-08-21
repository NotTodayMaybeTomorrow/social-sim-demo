import os
import json
import praw
import numpy as np
from supabase import create_client, Client
from bert_score import score
from config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
)

# Supabase setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Reddit API setup
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
)


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


def test_reddit_connection():
    """Test if Reddit API credentials are working"""
    try:
        subreddit = reddit.subreddit("python")
        print(f"Reddit connection test: Connection succeeded.")
        return True
    except Exception as e:
        print(f"Reddit connection failed: {e}")
        return False


def fetch_reddit_posts(subreddit_name, submission_flair=None, is_nsfw=False, limit=100):
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

            posts.append(
                {
                    "title": submission.title,
                    "content": submission.selftext if submission.selftext else submission.title,
                    "url": submission.url,
                    "score": submission.score,
                    "flair": submission.link_flair_text,
                    "nsfw": submission.over_18,
                    "id": submission.id,
                }
            )

        return posts
    except Exception as e:
        print(f"Error fetching Reddit posts: {e}")
        return []


def find_similar_posts_bertscore(target_post, reddit_posts, top_k=10, model_type="microsoft/deberta-xlarge-mnli"):
    """Find most similar posts using BERTScore"""
    if not reddit_posts:
        return []

    target_text = f"{target_post['title']} {target_post['content']}"
    reddit_texts = [f"{post['title']} {post['content']}" for post in reddit_posts]

    print(f"Computing BERTScore similarities for {len(reddit_texts)} posts...")
    
    try:
        # Create references list (target_text repeated for each candidate)
        references = [target_text] * len(reddit_texts)
        
        # Calculate BERTScore
        # P: precision, R: recall, F1: F1-score
        P, R, F1 = score(
            cands=reddit_texts,  # candidate texts (Reddit posts)
            refs=references,     # reference texts (target post repeated)
            model_type=model_type,
            verbose=True,
            device="cpu"  # Change to "cuda" if you have GPU
        )
        
        # Convert to numpy arrays for easier manipulation
        f1_scores = F1.numpy()
        precision_scores = P.numpy()
        recall_scores = R.numpy()
        
        # Get top k based on F1 scores
        top_indices = np.argsort(f1_scores)[::-1][:top_k]
        
        similar_posts = []
        for idx in top_indices:
            post = reddit_posts[idx].copy()
            post["bertscore_f1"] = float(f1_scores[idx])
            post["bertscore_precision"] = float(precision_scores[idx])
            post["bertscore_recall"] = float(recall_scores[idx])
            similar_posts.append(post)
        
        return similar_posts
        
    except Exception as e:
        print(f"Error computing BERTScore: {e}")
        print("Falling back to simple text matching...")
        
        # Fallback to simple keyword matching if BERTScore fails
        target_words = set(target_text.lower().split())
        similarities = []
        
        for post in reddit_posts:
            post_text = f"{post['title']} {post['content']}".lower()
            post_words = set(post_text.split())
            
            # Jaccard similarity as fallback
            intersection = len(target_words & post_words)
            union = len(target_words | post_words)
            similarity = intersection / union if union > 0 else 0
            similarities.append(similarity)
        
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        similar_posts = []
        for idx in top_indices:
            post = reddit_posts[idx].copy()
            post["bertscore_f1"] = float(similarities[idx])  # Using Jaccard as fallback
            post["bertscore_precision"] = float(similarities[idx])
            post["bertscore_recall"] = float(similarities[idx])
            similar_posts.append(post)
        
        return similar_posts


def collect_data():
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
        limit=200,
    )

    print(f"Found {len(reddit_posts)} matching Reddit posts")

    if not reddit_posts:
        print("No matching posts found on Reddit")
        return None

    # Use BERTScore for similarity
    similar_posts = find_similar_posts_bertscore(latest_submission, reddit_posts, top_k=10)

    print("\nTop 10 most similar posts (using BERTScore):")
    print("=" * 50)
    
    final_data = []

    for i, post in enumerate(similar_posts, 1):
        print(f"{i}. Title: {post['title']}...")
        print(f"   Score: {post['score']} | BERTScore F1: {post['bertscore_f1']:.3f}")
        print(f"   Precision: {post['bertscore_precision']:.3f} | Recall: {post['bertscore_recall']:.3f}")
        print(f"   Flair: {post['flair']} | NSFW: {post['nsfw']}")
        print(f"   URL: {post['url']}")
        print("-" * 40)
        
        post_data = post.copy()
        post_data['top_level_comments'] = []

        try:
            submission = reddit.submission(id=post['id'])
            submission.comment_sort = 'top'

            for comment in submission.comments:
                if len(post_data['top_level_comments']) >= 10:
                    break
                
                if not isinstance(comment, praw.models.MoreComments) and comment.body:
                    comment_data = {
                        "score": comment.score,
                        "body": comment.body,
                        "author": comment.author.name if comment.author else "[deleted]",
                        "author_hot_comments": []
                    }
                    
                    if comment.author and comment.author.name != "[deleted]":
                        try:
                            for auth_comment in comment.author.comments.hot(limit=10):
                                if not isinstance(auth_comment, praw.models.MoreComments) and auth_comment.body:
                                    comment_data['author_hot_comments'].append({
                                        "score": auth_comment.score,
                                        "body": auth_comment.body
                                    })
                        except Exception as e:
                            print(f"   Error fetching comments for {comment.author.name}: {e}")
                            
                    post_data['top_level_comments'].append(comment_data)
        
        except Exception as e:
            print(f"   Error fetching comments for post {post['id']}: {e}")
        
        final_data.append(post_data)

    print("\nAll data has been saved to the 'final_data' list.")
    return final_data


if __name__ == "__main__":
    final_data = collect_data()
    if final_data:
        with open("reddit_data_bertscore.json", "w") as f:
            json.dump(final_data, f, indent=2)
        print("Data successfully written to reddit_data_bertscore.json")