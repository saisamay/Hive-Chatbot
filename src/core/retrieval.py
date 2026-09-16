import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class RetrievalEngine:
    def __init__(self, index_path="models/retrieval/faiss.index", metadata_path="models/retrieval/metadata.json"):
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.model = None
        self.index = None
        self.metadata = []
        
        self.outcome_weights = {
            "RESOLVED": 1.0,
            "UNKNOWN": 0.5,
            "UNRESOLVED": 0.2
        }
        
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.load()
            
    def load(self):
        print("Loading MiniLM embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"Loading FAISS index from {self.index_path}...")
        self.index = faiss.read_index(self.index_path)
        with open(self.metadata_path, 'r') as f:
            self.metadata = json.load(f)
            
    def build_index(self, precedents, batch_size=32):
        """
        precedents: list of dicts with 'text', 'root_tweet_id', 'intent', 'outcome_status'
        """
        print("Loading MiniLM embedding model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        texts = [p['text'] for p in precedents]
        print(f"Embedding {len(texts)} precedents...")
        embeddings = self.model.encode(texts, batch_size=batch_size, show_progress_bar=True)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings)
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension) # Inner product = cosine sim for normalized vectors
        self.index.add(embeddings)
        
        self.metadata = precedents
        
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f)
        print("Index saved successfully.")

    def extract_text(self, conversation):
        tweets = list(conversation['tweets'].values())
        return " ".join([t['text_clean'] for t in tweets]).lower() # Keep inbound and outbound context

    def retrieve(self, conversation, predicted_intent, top_k=5, fetch_k=50):
        if self.index is None or self.model is None:
            raise ValueError("Retrieval index not loaded.")
            
        query_text = self.extract_text(conversation)
        query_vec = self.model.encode([query_text])
        faiss.normalize_L2(query_vec)
        
        # Fetch top N by pure semantic similarity first
        semantic_scores, indices = self.index.search(query_vec, fetch_k)
        
        candidates = []
        for i, idx in enumerate(indices[0]):
            if idx == -1: continue # FAISS returns -1 if not enough results
            
            meta = self.metadata[idx]
            semantic_score = float(semantic_scores[0][i])
            
            # Policy/Capability Validity (Mock neutral for MVP)
            policy_validity = 1.0 
            
            # Intent Compatibility
            if meta.get('intent') == predicted_intent and predicted_intent != "UNKNOWN":
                intent_multiplier = 1.2
            else:
                intent_multiplier = 1.0
            
            # Outcome Quality
            outcome_status = meta.get('outcome_status', 'UNKNOWN')
            outcome_weight = self.outcome_weights.get(outcome_status, 0.5)
            
            # Final Score Formula
            final_score = semantic_score * intent_multiplier * outcome_weight * policy_validity
            
            candidates.append({
                "precedent_id": meta['root_tweet_id'],
                "semantic_score": semantic_score,
                "outcome_status": outcome_status,
                "intent_compatibility_multiplier": intent_multiplier,
                "policy_capability_validity": policy_validity,
                "outcome_quality_weight": outcome_weight,
                "final_retrieval_score": final_score,
                "relevant_text": meta['text'],
                "precedent_intent": meta.get('intent')
            })
            
        # Sort by final score
        candidates.sort(key=lambda x: x['final_retrieval_score'], reverse=True)
        
        return {
            "query_id": conversation.get("root_tweet_id", "unknown"),
            "predicted_intent": predicted_intent,
            "candidates": candidates[:top_k]
        }
