import json
import time
from typing import List, Dict, Any
import textwrap

import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np

# Import your Reddit collector
from data_collector import collect_data  

from config import GEMINI_API_KEY, GEMINI_MODEL_NAME

# ---------------- Gemini Config ----------------
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL_NAME)


# ---------------- Persona Generation ----------------
def generate_persona(comments_text: str, max_retries: int = 3):
    """
    Generates a persona from a block of comments using Gemini with rate limiting.
    """
    if len(comments_text) > 2000:
        comments_text = comments_text[:2000] + "..."
    
    prompt = f"""Create persona from comments. JSON only:

{{
  "interests": ["hobby1", "hobby2"],
  "personality_traits": ["trait1", "trait2"],
  "likely_demographics": "brief desc (<= 50 words)"
}}

Comments:
{comments_text}"""
    
    # Configure generation parameters
    generation_config = genai.types.GenerationConfig(
        temperature=1.0,
        # max_output_tokens=1024,  # Adjust as needed
        top_p=0.95,              # Optional: controls nucleus sampling, Higher = more diverse vocabulary
        top_k=100                # Optional: controls top-k sampling, Higher = more word choices
    )

    for attempt in range(max_retries):
        try:
            time.sleep(4.5)
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            persona_data = json.loads(response_text.strip())
            return persona_data

        except json.JSONDecodeError as e:
            print(f"   JSON decode error (attempt {attempt+1}): {e}")
            if attempt == max_retries - 1:
                print(f"   Raw response: {response_text}")
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = 30 + (attempt * 10)
                print(f"   Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"   API error (attempt {attempt+1}): {e}")
        if attempt < max_retries - 1:
            time.sleep(2)
    
    print(f"   Failed to generate persona after {max_retries} attempts")
    return None


# ---------------- Clustering ----------------
def cluster_sentences(sentences: List[str], num_clusters: int = 10) -> Dict[int, List[str]]:
    """
    Cluster sentences into `num_clusters` groups using TF-IDF + KMeans.
    """
    vectorizer = TfidfVectorizer(stop_words="english")
    X = vectorizer.fit_transform(sentences)

    kmeans = KMeans(n_clusters=min(len(sentences), num_clusters), random_state=42, n_init="auto")
    labels = kmeans.fit_predict(X)

    clusters = {}
    for label, sentence in zip(labels, sentences):
        clusters.setdefault(label, []).append(sentence)
    return clusters, X, kmeans


# ---------------- Visualization ----------------
def visualize_clusters_with_legend(X, labels, personas, title="Sentence Clusters"):
    """
    Plot clusters in 2D using PCA, showing centroids and cluster borders.
    Legend shows persona info with line wrapping.
    """
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X.toarray())

    plt.figure(figsize=(12, 8))
    unique_labels = sorted(set(labels))
    colors = plt.cm.tab10.colors

    # Scatter points
    for lbl in unique_labels:
        points = coords[np.array(labels) == lbl]
        plt.scatter(points[:, 0], points[:, 1], color=colors[lbl % len(colors)], alpha=0.7)

        # Draw ellipse around cluster (approximate border)
        if len(points) > 1:
            cov = np.cov(points, rowvar=False)
            mean = points.mean(axis=0)
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = eigvals.argsort()[::-1]
            eigvals, eigvecs = eigvals[order], eigvecs[:, order]
            angle = np.degrees(np.arctan2(*eigvecs[:,0][::-1]))
            width, height = 2 * np.sqrt(eigvals)
            ellipse = Ellipse(xy=mean, width=width, height=height, angle=angle, edgecolor=colors[lbl % len(colors)],
                              fc='None', lw=1.5, ls='--')
            plt.gca().add_patch(ellipse)

        # Mark centroid
        centroid = coords[np.array(labels) == lbl].mean(axis=0)
        plt.scatter(*centroid, color=colors[lbl % len(colors)], marker='X', s=150, edgecolor='k')

    # Legend with line-wrapped persona info
    legend_labels = []
    for idx, persona in enumerate(personas):
        label = f"Persona {persona['persona_id']}: "
        traits = ", ".join(persona.get("personality_traits", []))
        interests = ", ".join(persona.get("interests", []))
        label += f"[Traits: {traits}] [Interests: {interests}]"
        wrapped_label = "\n".join(textwrap.wrap(label, width=40))
        legend_labels.append(wrapped_label)

    handles = [plt.Line2D([0], [0], marker='o', color='w',
                          markerfacecolor=colors[i % len(colors)], markersize=10)
               for i in range(len(unique_labels))]

    plt.legend(handles, legend_labels, bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    plt.title(title)
    plt.xlabel("PCA Component 1")
    plt.ylabel("PCA Component 2")
    plt.tight_layout()
    plt.show()


# ---------------- Persona Builder ----------------
def create_personas_from_reddit_data(data: List[Dict[str, Any]], num_clusters: int = 10):
    """
    Extract sentences from Reddit comments, cluster them, generate personas, and visualize clusters.
    """
    sentences = []
    for post in data:
        for comment in post.get("top_level_comments", []):
            if comment.get("body"):
                sentences.append(comment["body"])
            if len(sentences) >= 100:
                break
        if len(sentences) >= 100:
            break

    print(f"Collected {len(sentences)} sentences for clustering")

    # Cluster sentences
    clusters, X, kmeans_model = cluster_sentences(sentences, num_clusters=num_clusters)

    personas = []
    persona_counter = 1
    for cluster_id, cluster_sents in clusters.items():
        comments_text = "\n".join([f"- {s}" for s in cluster_sents])
        print(f"\nGenerating persona {persona_counter} from cluster {cluster_id}...")

        persona = generate_persona(comments_text)
        if persona:
            persona["persona_id"] = f"persona_{persona_counter}"
            persona["generated_from_cluster"] = cluster_sents
            personas.append(persona)
            print(f"   ✅ Created persona_{persona_counter}")
            persona_counter += 1
        else:
            print(f"   ❌ Failed for cluster {cluster_id}")

    print(f"\nGenerated {len(personas)} personas total")

    # Visualize clusters with line-wrapped legend
    visualize_clusters_with_legend(X, kmeans_model.labels_, personas)

    return personas


# ---------------- Example Run ----------------
if __name__ == "__main__":
    reddit_data = collect_data()
    if reddit_data:
        personas = create_personas_from_reddit_data(reddit_data, num_clusters=10)
        with open("personas.json", "w") as f:
            json.dump(personas, f, indent=2)
        print("Personas saved to personas.json")
