from typing import Tuple, Optional

class IntentClassifier:
    """
    Guardrail to detect out-of-scope intents (advisory, performance).
    Based on PRD and architecture rules.
    """
    
    # Keyword matches as per architecture.md
    ADVISORY_KEYWORDS = ["should i", "buy", "sell", "recommend", "better than", "which fund"]
    PERFORMANCE_KEYWORDS = ["returns", "performance", "cagr", "nav history"]
    
    def classify_intent(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Scans query for restricted intents.
        Returns (is_blocked, blocked_reason)
        """
        query_lower = query.lower()
        
        # Check advisory/buy-sell intent
        if any(keyword in query_lower for keyword in self.ADVISORY_KEYWORDS):
            return True, "I cannot provide investment advice or recommendations. Please visit Groww's learning centre for educational content or consult a financial advisor."
            
        # Check performance intent
        if any(keyword in query_lower for keyword in self.PERFORMANCE_KEYWORDS):
            return True, "I cannot provide historical returns or performance data. Please refer to the official fund factsheet on Groww for performance information."
            
        return False, None
