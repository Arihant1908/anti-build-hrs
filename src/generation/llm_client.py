import os
from dotenv import load_dotenv
from mistralai.client import Mistral
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception

def is_rate_limit(exception: Exception) -> bool:
    """Check if the exception is a rate limit (HTTP 429) error."""
    error_str = str(exception).lower()
    return "429" in error_str or "rate limit" in error_str

class LLMClient:
    """
    Client for interacting with Mistral AI.
    Based on PRD and architecture rules.
    """
    
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            # We don't raise an exception immediately so it can fail gracefully later, 
            # or the user can set it.
            print("Warning: MISTRAL_API_KEY is not set in environment variables.")
            self.client = None
        else:
            self.client = Mistral(api_key=api_key)
            
        self.model = os.getenv("LLM_MODEL", "mistral-small-latest")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "250"))
        
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(is_rate_limit),
        reraise=True
    )
    def _call_api(self, prompt: str):
        """Internal method to call the API, decorated with tenacity for retries."""
        return self.client.chat.complete(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )

    def generate_answer(self, prompt: str) -> str:
        """
        Calls Mistral API to generate the final answer with robust exponential backoff.
        """
        if not self.client:
            return "Error: LLM API key not configured. Please add MISTRAL_API_KEY to your .env file."
            
        try:
            chat_response = self._call_api(prompt)
            return chat_response.choices[0].message.content
        except Exception as e:
            # Fallback error handling as per architecture.md if not a rate limit or out of retries
            return f"I'm sorry, I encountered an error while generating the response: {str(e)}. Please try again later."
