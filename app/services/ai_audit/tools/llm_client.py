import os
import json
import requests
from typing import List, Dict

# Attempt to load LLM call generically
def call_llm_json(prompt: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {}
        
        # Using Gemini via requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        # We prompt it to output valid JSON
        sys_prompt = prompt + "\n\nCRITICAL: You must output ONLY a valid JSON object. No explanation, no markdown blocks."
        
        response = requests.post(url, json={"contents": [{"parts": [{"text": sys_prompt}]}]})
        if response.status_code == 200:
            text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            try:
                # Strip markdown code blocks if gemini returned them
                if text.startswith("```json"):
                    text = text[7:-3]
                elif text.startswith("```"):
                    text = text[3:-3]
                return json.loads(text.strip())
            except:
                return {}
        return {}
        
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "response_format": { "type": "json_object" },
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        content = response.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(content)
        except:
            return {}
    return {}
