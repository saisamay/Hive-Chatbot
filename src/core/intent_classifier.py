import joblib
import os
import numpy as np
from src.label_gold_set_cli import TAXONOMY

class IntentClassifier:
    def __init__(self, model_path="models/intent_classifier.joblib"):
        self.model_path = model_path
        self.pipeline = None
        self.unknown_threshold = 0.0
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            data = joblib.load(self.model_path)
            self.pipeline = data['pipeline']
            self.unknown_threshold = data.get('unknown_threshold', 0.5)

    def save(self, pipeline, unknown_threshold):
        self.pipeline = pipeline
        self.unknown_threshold = unknown_threshold
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            'pipeline': self.pipeline,
            'unknown_threshold': self.unknown_threshold
        }, self.model_path)

    def extract_text(self, conversation):
        tweets = list(conversation['tweets'].values())
        return " ".join([t['text_clean'] for t in tweets if t['inbound']]).lower()

    def predict(self, conversation):
        if not self.pipeline:
            raise ValueError("Model not loaded/trained.")

        text = self.extract_text(conversation)
        
        # Get probability distribution
        probas = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        
        # Sort indices by probability
        top_k_indices = np.argsort(probas)[::-1]
        
        top_k_candidates = [{"intent": classes[i], "confidence": float(probas[i])} for i in top_k_indices[:3]]
        
        primary_intent = classes[top_k_indices[0]]
        confidence = float(probas[top_k_indices[0]])
        
        # Apply strict UNKNOWN threshold
        if confidence < self.unknown_threshold:
            primary_intent = "UNKNOWN"
            
        return {
            "root_tweet_id": conversation["root_tweet_id"],
            "primary_intent": primary_intent,
            "confidence": confidence,
            "top_k_candidates": top_k_candidates,
            # We must output the remaining expected fields as fallback for downstream tasks
            "secondary_intents": [],
            "is_multi_intent": False,
            "trust_tier": "HUMAN_ESCALATION", # default
            "frustration_trajectory": "UNKNOWN",
            "safety": "SAFE",
            "capability": "UNKNOWN",
            "resolution": "UNRESOLVED"
        }
