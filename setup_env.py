"""
Setup script to configure the .env file with your API keys.
Run this once before using the retrieval pipeline.

Usage:
    python setup_env.py
"""
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"

# Default config values (non-sensitive)
DEFAULTS = {
    "CHROMA_PERSIST_PATH": "data/chroma_db/",
    "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
    "LLM_MODEL": "mistral-small-latest",
    "LLM_TEMPERATURE": "0.1",
    "LLM_MAX_TOKENS": "250",
    "RETRIEVAL_TOP_K": "3",
    "SIMILARITY_THRESHOLD": "0.3",
}

def main():
    print("=" * 50)
    print("  HDFC RAG Chatbot — Environment Setup")
    print("=" * 50)
    print()

    # Check if .env already exists and has a real key
    existing_key = None
    if ENV_PATH.exists():
        with open(ENV_PATH, "r") as f:
            for line in f:
                if line.startswith("MISTRAL_API_KEY="):
                    val = line.strip().split("=", 1)[1]
                    if val and val != "your_mistral_api_key_here":
                        existing_key = val
                        break

    if existing_key:
        print(f"  A Mistral API key is already configured (ends with ...{existing_key[-4:]})")
        overwrite = input("  Do you want to replace it? (y/N): ").strip().lower()
        if overwrite != "y":
            print("\n  Keeping existing key. Setup complete!")
            return
    
    # Prompt for the API key
    print("  You need a Mistral API key to use the LLM.")
    print("  Get one at: https://console.mistral.ai/api-keys/")
    print()
    api_key = input("  Enter your MISTRAL_API_KEY: ").strip()

    if not api_key:
        print("\n  No key entered. Exiting without changes.")
        return

    # Write the .env file
    lines = [f"MISTRAL_API_KEY={api_key}"]
    for key, value in DEFAULTS.items():
        lines.append(f"{key}={value}")

    with open(ENV_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    print()
    print("  .env file saved successfully!")
    print(f"  Location: {ENV_PATH}")
    print()
    print("  You can now run the retrieval pipeline:")
    print("    C:\\Users\\ariha\\anaconda\\python.exe -m src.retrieval.retriever")
    print()

if __name__ == "__main__":
    main()
