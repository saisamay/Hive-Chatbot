import json
import random
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import MiniBatchKMeans

def sample_gold_set(input_path="data/processed/amazon_threads.json", output_path="data/gold_set/unlabeled_sample.json", target_size=200):
    print("Loading conversations...")
    with open(input_path, 'r') as f:
        conversations = json.load(f)
        
    print(f"Total conversations: {len(conversations)}")
    
    # Filter English
    en_convs = [c for c in conversations if c.get("inbound_language") == "en"]
    print(f"English conversations: {len(en_convs)}")
    
    # We will sample 20,000 to do embedding/clustering quickly, then select 200 from them
    random.seed(42)
    sample_pool = random.sample(en_convs, min(20000, len(en_convs)))
    
    # Extract first inbound messages for embedding
    texts = []
    valid_pool = []
    
    for conv in sample_pool:
        inbounds = [m for m in conv["tweets"].values() if m["inbound"]]
        if not inbounds: continue
        inbounds.sort(key=lambda x: x["turn_index"])
        text = inbounds[0]["text_clean"]
        if len(text.split()) > 3:
            texts.append(text)
            valid_pool.append(conv)
            
    print(f"Embedding {len(texts)} messages...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    
    print("Clustering for semantic diversity (K=20)...")
    k = 20
    kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=1024)
    kmeans.fit(embeddings)
    
    labels = kmeans.labels_
    centroids = kmeans.cluster_centers_
    distances = kmeans.transform(embeddings) # distances to all centroids
    
    selected_indices = set()
    
    # A. Semantic diversity (5 per cluster = 100)
    for i in range(k):
        cluster_idx = np.where(labels == i)[0]
        if len(cluster_idx) > 0:
            local_dists = distances[cluster_idx, i]
            closest = cluster_idx[np.argsort(local_dists)[:5]]
            selected_indices.update(closest)
        
    # B. Ambiguity (Cases where distance to top 2 centroids is very close)
    sorted_dists = np.sort(distances, axis=1)
    diffs = sorted_dists[:, 1] - sorted_dists[:, 0]
    ambiguous_idx = np.argsort(diffs)[:20]
    selected_indices.update(ambiguous_idx)
    
    # C. Multi-intent (Long messages with multiple clauses/questions)
    multi_intent_candidates = []
    for i, t in enumerate(texts):
        if t.count('?') > 1 or (len(t.split()) > 30 and ('and' in t.lower() or 'also' in t.lower())):
            multi_intent_candidates.append(i)
    if multi_intent_candidates:
        selected_indices.update(random.sample(multi_intent_candidates, min(20, len(multi_intent_candidates))))
    
    # D. Frustration / repetition
    frustration_kw = ['terrible', 'worst', 'awful', 'angry', 'upset', 'disappointed', 'ridiculous', 'sucks', 'joke', 'wasted']
    frustration_cands = [i for i, t in enumerate(texts) if any(kw in t.lower() for kw in frustration_kw)]
    if frustration_cands:
        selected_indices.update(random.sample(frustration_cands, min(20, len(frustration_cands))))
    
    # E. Escalation-prone cases
    escalation_kw = ['call me', 'manager', 'human', 'contact me', 'supervisor', 'lawyer', 'sue', 'police', 'ombudsman', 'trading standards']
    escalation_cands = [i for i, t in enumerate(texts) if any(kw in t.lower() for kw in escalation_kw)]
    if escalation_cands:
        selected_indices.update(random.sample(escalation_cands, min(20, len(escalation_cands))))
    
    # F. Long-tail / unusual cases (furthest from their own centroid)
    outlier_idx = []
    for i in range(k):
        cluster_idx = np.where(labels == i)[0]
        if len(cluster_idx) > 0:
            local_dists = distances[cluster_idx, i]
            furthest = cluster_idx[np.argsort(local_dists)[-1]]
            outlier_idx.append(furthest)
    selected_indices.update(outlier_idx)
    
    # Ensure exactly target_size
    selected_list = list(selected_indices)
    if len(selected_list) > target_size:
        selected_list = random.sample(selected_list, target_size)
    elif len(selected_list) < target_size:
        remaining = list(set(range(len(valid_pool))) - selected_indices)
        needed = target_size - len(selected_list)
        selected_list.extend(random.sample(remaining, needed))
        
    final_sample = [valid_pool[i] for i in selected_list]
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(final_sample, f, indent=2)
        
    print(f"\nSuccessfully sampled exactly {len(final_sample)} conversations.")
    
    # Diagnostics: Taxonomy coverage
    # (Just an estimate based on cluster labels for reporting)
    sampled_labels = [labels[i] for i in selected_list]
    cluster_counts = {i: sampled_labels.count(i) for i in range(k)}
    print("\nDiagnostic - Sample distribution across 20 semantic regions:")
    for cluster_id, count in sorted(cluster_counts.items()):
        print(f"Cluster {cluster_id}: {count} cases")
        
    print(f"\nSaved to {output_path}")

if __name__ == "__main__":
    sample_gold_set()
