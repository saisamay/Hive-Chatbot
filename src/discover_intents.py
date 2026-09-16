import json
import random
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans
import os

def run_discovery():
    print("Loading data...")
    with open('data/processed/amazon_threads.json', 'r') as f:
        conversations = json.load(f)
        
    print(f"Total conversations: {len(conversations)}")
    
    inbound_texts = []
    
    for conv in conversations:
        # Step 2: Analysis corpus - English subset
        if conv.get("inbound_language") != "en":
            continue
            
        # Step 1: Analysis unit - First inbound message of the conversation
        # This represents the primary reason for contact
        tweets = conv["tweets"]
        inbound_msgs = [m for m in tweets.values() if m["inbound"]]
        if not inbound_msgs:
            continue
            
        # Sort by turn_index and get the first one
        inbound_msgs.sort(key=lambda x: x["turn_index"])
        first_msg = inbound_msgs[0]
        
        text = first_msg["text_clean"]
        if len(text.split()) > 3: # Ignore extremely short messages like "Help" or "[PERSON_1]"
            inbound_texts.append(text)
            
    print(f"English inbound messages suitable for analysis: {len(inbound_texts)}")
    
    # Sample 15,000 for CPU efficiency
    sample_size = min(15000, len(inbound_texts))
    random.seed(42)
    sampled_texts = random.sample(inbound_texts, sample_size)
    print(f"Sampled {sample_size} messages for clustering.")
    
    # Step 3: Semantic representation
    print("Loading sentence-transformers model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Encoding messages...")
    embeddings = model.encode(sampled_texts, show_progress_bar=True, convert_to_numpy=True)
    
    # Step 4: Discover clusters
    print("Clustering embeddings...")
    num_clusters = 20 # Over-cluster slightly to find distinct groups, then merge into 6-10 intents
    kmeans = MiniBatchKMeans(n_clusters=num_clusters, random_state=42, batch_size=1024)
    kmeans.fit(embeddings)
    
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_
    
    # Step 5: Inspect representative examples
    os.makedirs('scratch', exist_ok=True)
    with open('scratch/cluster_output.txt', 'w') as f:
        f.write(f"Cluster Analysis Output (K={num_clusters})\n")
        f.write("="*40 + "\n\n")
        
        for i in range(num_clusters):
            cluster_indices = np.where(labels == i)[0]
            cluster_size = len(cluster_indices)
            f.write(f"Cluster {i} (Size: {cluster_size} - {cluster_size/sample_size*100:.1f}%)\n")
            f.write("-" * 30 + "\n")
            
            # Find closest examples to centroid
            cluster_embeddings = embeddings[cluster_indices]
            centroid = centroids[i]
            distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
            
            # Get top 15 closest
            closest_local_indices = np.argsort(distances)[:15]
            closest_global_indices = cluster_indices[closest_local_indices]
            
            for idx in closest_global_indices:
                f.write(f"- {sampled_texts[idx]}\n")
            
            f.write("\n")
            
    print("Clustering complete. Results written to scratch/cluster_output.txt")

if __name__ == "__main__":
    run_discovery()
