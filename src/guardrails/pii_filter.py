import re
from typing import Tuple, Optional

class PIIFilter:
    """
    Guardrail to detect and block PII (Personally Identifiable Information).
    Based on PRD and architecture rules.
    """
    
    # Regex patterns defined in architecture.md
    PATTERNS = {
        "PAN": r"[A-Za-z]{5}\d{4}[A-Za-z]",
        "Aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "Email": r"[\w.-]+@[\w.-]+\.\w+",
        "Phone": r"(\+91[\-\s]?)?[6-9]\d{9}",
        "OTP": r"\b(otp|code|pin)\b\s*[:\-]?\s*\b\d{4,6}\b" # Contextual OTP
    }
    
    def __init__(self):
        self.compiled_patterns = {name: re.compile(pattern, re.IGNORECASE) 
                                  for name, pattern in self.PATTERNS.items()}
                                  
    def check_pii(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Scans text for PII. 
        Returns (has_pii, blocked_reason)
        """
        for pii_type, pattern in self.compiled_patterns.items():
            if pattern.search(text):
                return True, f"Detected sensitive information ({pii_type}). For your security, please do not share personal details."
                
        return False, None
