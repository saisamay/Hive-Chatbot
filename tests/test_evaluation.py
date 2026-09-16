import os
import json
import unittest
from src.evaluation.harness import Evaluator
from src.evaluation.baselines import TrivialIntentBaseline, StaticPolicyBaseline

class TestEvaluationHarness(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.gold_set_path = "data/gold/gold_200_labeled.json"
        # Only run tests if the gold set actually exists
        if os.path.exists(cls.gold_set_path):
            cls.evaluator = Evaluator(cls.gold_set_path)
            with open("tests/fixtures/mock_threads.json", "r") as f:
                cls.threads = json.load(f)
        else:
            cls.evaluator = None

    def test_evaluator_loads_200_cases(self):
        if not self.evaluator:
            self.skipTest("Gold set not found")
        self.assertEqual(len(self.evaluator.gold_cases), 200)
        
    def test_baselines_run_successfully(self):
        if not self.evaluator:
            self.skipTest("Gold set not found")
            
        trivial_baseline = TrivialIntentBaseline()
        static_baseline = StaticPolicyBaseline()
        
        trivial_preds = []
        static_preds = []
        
        for case in self.evaluator.gold_cases:
            root_id = case['root_tweet_id']
            # We need the conversation data to pass to the baselines
            # Since the golden set only has labels, we'll mock the input for now
            # or find the corresponding thread in processed data
            
            # Mock thread_data for baseline testing
            thread_data = {
                "root_tweet_id": root_id,
                "tweets": {
                    "mock_id": {"text_clean": "where is my refund?", "inbound": True}
                }
            }
                
            trivial_preds.append(trivial_baseline.predict(thread_data))
            static_preds.append(static_baseline.predict(thread_data))
            
        # Run harness
        res_trivial, _ = self.evaluator.evaluate(trivial_preds, run_name="trivial_baseline_test")
        res_static, _ = self.evaluator.evaluate(static_preds, run_name="static_baseline_test")
        
        self.assertIn("accuracy", res_trivial["intent"])
        self.assertIn("macro_f1", res_trivial["intent"])
        self.assertIn("confusion_matrix", res_static["trust_gate"])
        self.assertIn("recall", res_static["safety"])

if __name__ == '__main__':
    unittest.main()
