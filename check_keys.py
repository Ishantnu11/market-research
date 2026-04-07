import os
import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv()

# 1. Test Gemini
print("--- TESTING GEMINI ---")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
try:
    for m in genai.list_models():
        print(f"Gemini Success: Found model {m.name}")
        break
except Exception as e:
    print(f"Gemini FAILED: {e}")

# 2. Test Tavily
print("\n--- TESTING TAVILY ---")
tav_key = os.getenv("TAVILY_API_KEY")
try:
    resp = requests.post("https://api.tavily.com/search", json={
        "api_key": tav_key,
        "query": "test",
        "max_results": 1
    })
    if resp.status_code == 200:
        print("Tavily Success!")
    else:
        print(f"Tavily FAILED: {resp.status_code} {resp.text}")
except Exception as e:
    print(f"Tavily FAILED: {e}")

# 3. Test Groq
print("\n--- TESTING GROQ ---")
groq_key = os.getenv("GROQ_API_KEY")
try:
    resp = requests.post("https://api.groq.com/openai/v1/chat/completions", 
        headers={"Authorization": f"Bearer {groq_key}"},
        json={
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5
        }
    )
    if resp.status_code == 200:
        print("Groq Success!")
    else:
        print(f"Groq FAILED: {resp.status_code} {resp.text}")
except Exception as e:
    print(f"Groq FAILED: {e}")
