import os
import unittest
import numpy as np
from src.core.retrieval import RetrievalEngine

class TestRetrievalEngine(unittest.TestCase):
    def setUp(self):
        self.index_path = "models/retrieval_test/faiss.index"
        self.metadata_path = "models/retrieval_test/metadata.json"
        self.engine = RetrievalEngine(index_path=self.index_path, metadata_path=self.metadata_path)
        
    def tearDown(self):
        if os.path.exists(self.index_path):
            os.remove(self.index_path)
        if os.path.exists(self.metadata_path):
            os.remove(self.metadata_path)
        if os.path.exists("models/retrieval_test"):
            os.rmdir("models/retrieval_test")
            
    def test_build_and_retrieve(self):
        precedents = [
            {
                "root_tweet_id": "p1",
                "intent": "Delivery_Delayed",
                "outcome_status": "RESOLVED",
                "text": "where is my package? it arrived late thanks."
            },
            {
                "root_tweet_id": "p2",
                "intent": "Delivery_Delayed",
                "outcome_status": "UNRESOLVED",
                "text": "where is my package? this is useless."
            },
            {
                "root_tweet_id": "p3",
                "intent": "UNKNOWN",
                "outcome_status": "UNKNOWN",
                "text": "hello"
            }
        ]
        
        # Build index
        self.engine.build_index(precedents)
        
        self.assertIsNotNone(self.engine.index)
        self.assertEqual(len(self.engine.metadata), 3)
        
        # Query
        query_conversation = {
            "root_tweet_id": "q1",
            "tweets": {
                "1": {"text_clean": "where is my package?", "inbound": True}
            }
        }
        
        results = self.engine.retrieve(query_conversation, predicted_intent="Delivery_Delayed", top_k=3)
        
        self.assertEqual(results["query_id"], "q1")
        self.assertEqual(results["predicted_intent"], "Delivery_Delayed")
        
        candidates = results["candidates"]
        self.assertEqual(len(candidates), 3)
        
        # Check outcome weighting: p1 (RESOLVED, 1.0) should outrank p2 (UNRESOLVED, 0.2)
        # even if they have extremely similar semantic match to the query.
        self.assertEqual(candidates[0]["precedent_id"], "p1")
        self.assertEqual(candidates[0]["outcome_status"], "RESOLVED")
        self.assertEqual(candidates[0]["outcome_quality_weight"], 1.0)
        
        # p2 should be penalized heavily
        p2_candidate = next(c for c in candidates if c["precedent_id"] == "p2")
        self.assertEqual(p2_candidate["outcome_quality_weight"], 0.2)
        
        # p3 is UNKNOWN
        p3_candidate = next(c for c in candidates if c["precedent_id"] == "p3")
        self.assertEqual(p3_candidate["outcome_quality_weight"], 0.5)
        
        # Test UNKNOWN intent compatibility
        results_unk = self.engine.retrieve(query_conversation, predicted_intent="UNKNOWN", top_k=3)
        unk_candidates = results_unk["candidates"]
        p3_unk_candidate = next(c for c in unk_candidates if c["precedent_id"] == "p3")
        self.assertEqual(p3_unk_candidate["intent_compatibility_multiplier"], 1.0)

if __name__ == '__main__':
    unittest.main()
