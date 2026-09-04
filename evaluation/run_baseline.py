import sys
import os
import json
import requests
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def call_llm(prompt: str) -> str:
    # Use OpenAI API as default backend
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "ERROR_NO_API_KEY"
            
        # Using Gemini via requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if response.status_code == 200:
            return response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return f"API ERROR {response.status_code}"
        
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"API Error: {response.status_code} - {response.text}"

def run_baseline_for_case(case_path: str):
    with open(case_path, 'r') as f:
        case = json.load(f)
        
    prompt = f"Analyze this trading history and identify important performance and behavioral patterns. Explain your findings.\n\nTrading History:\n{json.dumps(case['trades'], indent=2)}"
    
    result = call_llm(prompt)
    return result

def run_all():
    cases_dir = "cases"
    results = []
    cases_dir_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), cases_dir)
    print("Running baseline evaluation...")
    
    files = sorted([f for f in os.listdir(cases_dir_abs) if f.endswith(".json")])
    for filename in files:
        print(f"Evaluating {filename}...")
        case_id = filename.split("_")[1].split(".")[0]
        
        with open(os.path.join(cases_dir_abs, filename), 'r') as f:
            ground_truth = json.load(f)["pattern"]
            
        start_time = time.time()
        llm_result = run_baseline_for_case(os.path.join(cases_dir_abs, filename))
        elapsed = time.time() - start_time
        
        if llm_result == "ERROR_NO_API_KEY":
            print("Failed: No API Key found.")
            sys.exit(1)
            
        results.append({
            "case_id": case_id,
            "ground_truth_pattern": ground_truth,
            "baseline_response": llm_result,
            "time_seconds": elapsed,
            "cost_estimate": 0.001 
        })
        
        # Save incrementally
        results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, "baseline_results.json"), "w") as f:
            json.dump(results, f, indent=2)
                
    print("Baseline evaluation complete. Results saved to evaluation/results/baseline_results.json")

if __name__ == "__main__":
    run_all()
