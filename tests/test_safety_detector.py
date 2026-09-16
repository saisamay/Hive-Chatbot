import unittest
from src.core.safety_detector import SafetyDetector

class TestSafetyDetector(unittest.TestCase):
    def setUp(self):
        self.detector = SafetyDetector()

    def test_genuine_serious_safety_concern(self):
        # Should flag physical safety risks
        conv = {"text_clean": "the driver was driving a dangerous truck and almost hit my kid"}
        self.assertEqual(self.detector.evaluate(conv), "SAFETY_CONCERN")
        
        conv2 = {"text_clean": "i am going to harm myself if this isn't fixed"}
        self.assertEqual(self.detector.evaluate(conv2), "SAFETY_CONCERN")

    def test_serious_legal_concern(self):
        # Should flag explicit legal threats with context
        conv = {"text_clean": "i am filing a lawsuit against amazon for this breach of contract"}
        self.assertEqual(self.detector.evaluate(conv), "SAFETY_CONCERN")
        
        conv2 = {"text_clean": "a report has been filed with the police"}
        self.assertEqual(self.detector.evaluate(conv2), "SAFETY_CONCERN")
        
        conv3 = {"text_clean": "my bank account got drained and identity theft"}
        self.assertEqual(self.detector.evaluate(conv3), "SAFETY_CONCERN")

    def test_ordinary_frustration(self):
        # Should NOT flag ordinary frustration
        conv = {"text_clean": "i am very angry and frustrated with your terrible service"}
        self.assertEqual(self.detector.evaluate(conv), "SAFE")

    def test_profanity_without_safety(self):
        # Should NOT flag pure profanity
        conv = {"text_clean": "where the fuck is my shit? this is bullshit."}
        self.assertEqual(self.detector.evaluate(conv), "SAFE")

    def test_ambiguous_safety_language(self):
        # Should flag as UNKNOWN for conservative manual review
        conv = {"text_clean": "you guys stole my money, this is fraud"}
        self.assertEqual(self.detector.evaluate(conv), "UNKNOWN")
        
        conv2 = {"text_clean": "my account got hacked wtf"}
        self.assertEqual(self.detector.evaluate(conv2), "SAFETY_CONCERN") # Wait, 'account got hacked' is a serious pattern.
        
        conv3 = {"text_clean": "i'm going to sue you"}
        self.assertEqual(self.detector.evaluate(conv3), "UNKNOWN") # "sue" is ambiguous
        
        conv4 = {"text_clean": "call the police on your delivery driver"}
        self.assertEqual(self.detector.evaluate(conv4), "UNKNOWN") # "police" is ambiguous
        
if __name__ == '__main__':
    unittest.main()
