import os
import unittest
from src.core.intent_classifier import IntentClassifier

class TestIntentClassifier(unittest.TestCase):
    def setUp(self):
        self.model_path = "models/intent_classifier.joblib"
        if not os.path.exists(self.model_path):
            self.skipTest("Model not trained yet.")
        self.classifier = IntentClassifier(model_path=self.model_path)
        
    def test_model_loading(self):
        self.assertIsNotNone(self.classifier.pipeline)
        self.assertGreater(self.classifier.unknown_threshold, 0.0)
        
    def test_prediction_shape(self):
        mock_conversation = {
            "root_tweet_id": "123",
            "tweets": {
                "1": {"text_clean": "where is my refund?", "inbound": True}
            }
        }
        pred = self.classifier.predict(mock_conversation)
        
        self.assertEqual(pred["root_tweet_id"], "123")
        self.assertIn("primary_intent", pred)
        self.assertIn("confidence", pred)
        self.assertIn("top_k_candidates", pred)
        self.assertTrue(isinstance(pred["top_k_candidates"], list))
        
    def test_unknown_threshold(self):
        # Text highly unlikely to be predicted with confidence
        mock_conversation = {
            "root_tweet_id": "456",
            "tweets": {
                "1": {"text_clean": "ok sounds good", "inbound": True}
            }
        }
        
        # Override threshold to 1.0 to guarantee UNKNOWN
        original_threshold = self.classifier.unknown_threshold
        self.classifier.unknown_threshold = 1.0
        pred = self.classifier.predict(mock_conversation)
        self.assertEqual(pred["primary_intent"], "UNKNOWN")
        
        self.classifier.unknown_threshold = original_threshold

if __name__ == '__main__':
    unittest.main()
