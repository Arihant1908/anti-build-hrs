import unittest
import os
import time
from src.retrieval.retriever import RAGRetriever

class TestRetrieval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only setup retriever once for all tests to save model load time
        if not os.getenv("MISTRAL_API_KEY"):
            raise unittest.SkipTest("MISTRAL_API_KEY not set. Skipping integration tests.")
        cls.retriever = RAGRetriever()

    def test_r01_expense_ratio(self):
        query = "What is the expense ratio of HDFC Large Cap Fund?"
        start = time.time()
        result = self.retriever.process_query(query)
        latency = time.time() - start
        
        self.assertFalse(result.blocked)
        self.assertLess(latency, 5.0, "Latency exceeded 5 seconds limit")
        self.assertIn("groww.in/mutual-funds/hdfc-large-cap-fund", result.answer)
        self.assertTrue(len(result.answer.split('.')) <= 5, "Answer brevity exceeded 3 sentences") # Approx 3-5 sentences

    def test_r02_exit_load(self):
        query = "What is the exit load for HDFC Small Cap Fund?"
        result = self.retriever.process_query(query)
        self.assertFalse(result.blocked)
        self.assertIn("groww.in", result.answer)

    def test_r03_lock_in(self):
        query = "What is the ELSS lock-in period?"
        result = self.retriever.process_query(query)
        self.assertFalse(result.blocked)
        self.assertIn("3 years", result.answer.lower())
        self.assertIn("groww.in/mutual-funds/hdfc-elss-tax-saver", result.answer)

    def test_r07_citation_present(self):
        query = "Minimum SIP for HDFC Flexi Cap?"
        result = self.retriever.process_query(query)
        self.assertFalse(result.blocked)
        self.assertIn("groww.in", result.answer)
        self.assertIn("Last updated from sources:", result.answer)

if __name__ == "__main__":
    unittest.main()
