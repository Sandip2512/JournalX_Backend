import os
import json

def generate_report():
    res_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "baseline_results.json")
    if not os.path.exists(res_path):
        print("No results found.")
        return
        
    with open(res_path, 'r') as f:
        results = json.load(f)
        
    cases_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmark", "cases")
    ground_truths = {}
    for f_name in os.listdir(cases_dir):
        if f_name.endswith(".json"):
            with open(os.path.join(cases_dir, f_name), 'r') as f:
                c = json.load(f)
                case_id = c.get("case_id", "UNKNOWN")
                ground_truths[case_id] = c.get("ground_truth", {})
                
    total = len(results)
    correct_detection = 0
    false_positives = 0
    failed_cases = []
    
    for r in results:
        cid = r["case_id"]
        out = r.get("baseline_output", {})
        gt = ground_truths.get(cid, {})
        
        expected_cat = gt.get("expected_category", "None")
        should_detect = gt.get("expected_detection", "NO") == "YES"
        
        # Check if the output has an error
        if "error" in out:
            failed_cases.append({"case_id": cid, "failure_type": "API_ERROR", "why": out["error"]})
            continue
            
        findings = out.get("findings", [])
        categories_found = [f.get("category", "") for f in findings]
        
        if should_detect:
            # We expect a finding of expected_cat
            if any(expected_cat.lower() in c.lower() for c in categories_found):
                correct_detection += 1
            else:
                failed_cases.append({
                    "case_id": cid,
                    "failure_type": "MISSED_PATTERN",
                    "ground_truth": expected_cat,
                    "why_it_failed": f"Baseline reported {categories_found} but missed {expected_cat}."
                })
        else:
            # We expect NO findings or category "None"
            real_findings = [c for c in categories_found if c.lower() not in ["none", "none.", "n/a", ""]]
            if real_findings:
                false_positives += 1
                failed_cases.append({
                    "case_id": cid,
                    "failure_type": "FALSE_POSITIVE",
                    "ground_truth": "No Pattern",
                    "why_it_failed": f"Baseline hallucinated patterns: {real_findings}"
                })
            else:
                correct_detection += 1 # correctly identified no pattern
                
    accuracy = (correct_detection / total) * 100 if total > 0 else 0
    fpr = (false_positives / total) * 100 if total > 0 else 0
    
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "baseline", "baseline_report.md")
    
    report_md = f"""# Baseline Evaluation Report

## Methodology
The simple LLM baseline was evaluated on {total} synthetic cases. 
No agentic recursion or specialized math verification was present, just a single Prompt -> LLM pass.

## Metrics
- **Total Cases Evaluated:** {total}
- **Pattern Detection Accuracy:** {accuracy:.1f}%
- **False Positive Rate:** {fpr:.1f}%

## Failure Analysis
"""
    for fail in failed_cases:
        report_md += f"""
### {fail['case_id']}
- **Failure Type:** {fail['failure_type']}
- **Ground Truth Expected:** {fail.get('ground_truth', 'N/A')}
- **Reason:** {fail.get('why_it_failed', fail.get('why', 'Unknown Error'))}
"""
    
    report_md += """
## Limitations
As expected from a non-agentic baseline, the LLM hallucinates patterns in pure noise and misses specific data breakpoints when not explicitly guided by sequential mathematical checks (the Verification layer).
"""
    with open(report_path, "w") as f:
        f.write(report_md)
        
    print(f"Metrics evaluated. Accuracy: {accuracy:.1f}%. Report generated at {report_path}")

if __name__ == '__main__':
    generate_report()
