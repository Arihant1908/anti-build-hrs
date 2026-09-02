import unittest
import os
from src.retrieval.retriever import RAGRetriever

class TestEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Only setup retriever once
        if not os.getenv("MISTRAL_API_KEY"):
            raise unittest.SkipTest("MISTRAL_API_KEY not set. Skipping edge cases.")
        cls.retriever = RAGRetriever()

    def test_e01_out_of_scope_fund(self):
        query = "Tell me about Axis Bluechip"
        result = self.retriever.process_query(query)
        self.assertFalse(result.blocked)
        # Should not find relevant information or LLM will deny answering
        self.assertNotIn("groww.in/mutual-funds/axis-bluechip", result.answer)
        
    def test_e02_ambiguous_query(self):
        query = "expense ratio?"
        result = self.retriever.process_query(query)
        self.assertFalse(result.blocked)
        # We expect the LLM to complain about no context or state that it doesn't know which fund

    def test_e05_no_relevant_chunks(self):
        query = "What is the weather today?"
        result = self.retriever.process_query(query)
        self.assertFalse(result.blocked)
        self.assertIn("couldn't find relevant information", result.answer)

if __name__ == "__main__":
    unittest.main()
