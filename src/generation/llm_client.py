import os
from dotenv import load_dotenv
from mistralai.client import Mistral

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
        
    def generate_answer(self, prompt: str) -> str:
        """
        Calls Mistral API to generate the final answer.
        """
        if not self.client:
            return "Error: LLM API key not configured. Please add MISTRAL_API_KEY to your .env file."
            
        try:
            chat_response = self.client.chat.complete(
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
            return chat_response.choices[0].message.content
        except Exception as e:
            # Fallback error handling as per architecture.md
            return f"I'm sorry, I encountered an error while generating the response: {str(e)}. Please try again later."
