import os
import json
from dotenv import load_dotenv

load_dotenv()

def get_configured_client():
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        return {"provider": "openai", "client": OpenAI(api_key=os.environ["OPENAI_API_KEY"])}
    elif os.getenv("GEMINI_API_KEY"):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return {"provider": "gemini", "model": genai.GenerativeModel('gemini-1.5-flash')}
    return None

def call_llm(prompt: str) -> dict:
    conf = get_configured_client()
    if not conf:
        return {"error": "NO_API_KEY_FOUND"}
        
    try:
        if conf["provider"] == "openai":
            res = conf["client"].chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt + "\n\nCRITICAL: Output strictly valid JSON."}],
                temperature=0.2
            )
            raw = res.choices[0].message.content
        else:
            p = prompt + "\n\nCRITICAL: Output strictly valid JSON without markdown wrapping."
            res = conf["model"].generate_content(p)
            raw = res.text.strip()
            if raw.startswith("```json"): raw = raw[7:-3]
            elif raw.startswith("```"): raw = raw[3:-3]
            
        return json.loads(raw.strip())
    except Exception as e:
        return {"error": f"API_ERROR: {str(e)}"}

if __name__ == "__main__":
    out = call_llm("Return {\"hello\": \"world\"} in JSON")
    print(out)
