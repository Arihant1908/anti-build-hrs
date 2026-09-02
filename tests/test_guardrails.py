import unittest
from src.guardrails.pii_filter import PIIFilter
from src.guardrails.intent_classifier import IntentClassifier

class TestGuardrails(unittest.TestCase):
    def setUp(self):
        self.pii_filter = PIIFilter()
        self.intent_classifier = IntentClassifier()

    def test_g01_pan_detection(self):
        query = "My PAN is ABCDE1234F"
        has_pii, reason = self.pii_filter.check_pii(query)
        self.assertTrue(has_pii)
        self.assertIn("PAN", reason)

    def test_g02_aadhaar_detection(self):
        query = "Aadhaar: 1234 5678 9012"
        has_pii, reason = self.pii_filter.check_pii(query)
        self.assertTrue(has_pii)
        self.assertIn("Aadhaar", reason)

    def test_g03_email_detection(self):
        query = "Send to user@email.com"
        has_pii, reason = self.pii_filter.check_pii(query)
        self.assertTrue(has_pii)
        self.assertIn("Email", reason)

    def test_g04_phone_detection(self):
        query = "Call me at +91 9876543210"
        has_pii, reason = self.pii_filter.check_pii(query)
        self.assertTrue(has_pii)
        self.assertIn("Phone", reason)

    def test_g05_advisory_refusal(self):
        query = "Should I buy HDFC Small Cap?"
        is_blocked, reason = self.intent_classifier.classify_intent(query)
        self.assertTrue(is_blocked)
        self.assertIn("Groww's learning centre", reason)

    def test_g06_comparison_refusal(self):
        query = "Is HDFC Flexi Cap better than SBI Flexi Cap?"
        is_blocked, reason = self.intent_classifier.classify_intent(query)
        self.assertTrue(is_blocked)
        self.assertIn("Groww's learning centre", reason)

    def test_g07_performance_refusal(self):
        query = "What are the 5-year returns of this fund?"
        is_blocked, reason = self.intent_classifier.classify_intent(query)
        self.assertTrue(is_blocked)
        self.assertIn("factsheet", reason.lower())

    def test_g08_transactional_refusal(self):
        query = "Sell my ELSS units"
        is_blocked, reason = self.intent_classifier.classify_intent(query)
        self.assertTrue(is_blocked)
        self.assertIn("Groww's learning centre", reason)

if __name__ == "__main__":
    unittest.main()
