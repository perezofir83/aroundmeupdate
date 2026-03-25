"""Quick test to find working Claude model."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from main import load_config
load_config()

import anthropic
print(f"Anthropic SDK version: {anthropic.__version__}")

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

models = [
    "claude-sonnet-4-5-20250514",
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-haiku-20240307",
]

for model in models:
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say hi"}],
        )
        print(f"  {model} -> OK!")
        break
    except Exception as e:
        print(f"  {model} -> FAIL: {e}")
