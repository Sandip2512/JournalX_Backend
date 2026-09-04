# Baseline Evaluation Report

## Methodology
The simple LLM baseline was evaluated on 20 synthetic cases. 
No agentic recursion or specialized math verification was present, just a single Prompt -> LLM pass.

## Metrics
- **Total Cases Evaluated:** 20
- **Pattern Detection Accuracy:** 10.0%
- **False Positive Rate:** 75.0%

## Failure Analysis

### CASE_04_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_05_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Session']

### CASE_06_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Session']

### CASE_07_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Overtrading', 'Instrument']

### CASE_08_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_09_GENERIC
- **Failure Type:** API_ERROR
- **Ground Truth Expected:** N/A
- **Reason:** API_ERROR: Illegal trailing comma before end of object: line 20 column 169 (char 1880)

### CASE_10_GENERIC
- **Failure Type:** API_ERROR
- **Ground Truth Expected:** N/A
- **Reason:** API_ERROR: Illegal trailing comma before end of object: line 20 column 249 (char 1804)

### CASE_11_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_12_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_13_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_14_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_15_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_15_NO_PATTERN
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Session', 'Instrument', 'Overtrading']

### CASE_16_SMALL_SAMPLE
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Instrument', 'Overtrading']

### CASE_17_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_18_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_19_GENERIC
- **Failure Type:** FALSE_POSITIVE
- **Ground Truth Expected:** No Pattern
- **Reason:** Baseline hallucinated patterns: ['Overtrading', 'Instrument']

### CASE_20_GENERIC
- **Failure Type:** API_ERROR
- **Ground Truth Expected:** N/A
- **Reason:** API_ERROR: 429 You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. 
* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-3.6-flash
Please retry in 23.472316927s. [links {
  description: "Learn more about Gemini API quotas"
  url: "https://ai.google.dev/gemini-api/docs/rate-limits"
}
, violations {
  quota_metric: "generativelanguage.googleapis.com/generate_content_free_tier_requests"
  quota_id: "GenerateRequestsPerDayPerProjectPerModel-FreeTier"
  quota_dimensions {
    key: "model"
    value: "gemini-3.6-flash"
  }
  quota_dimensions {
    key: "location"
    value: "global"
  }
  quota_value: 20
}
, retry_delay {
  seconds: 23
}
]

## Limitations
As expected from a non-agentic baseline, the LLM hallucinates patterns in pure noise and misses specific data breakpoints when not explicitly guided by sequential mathematical checks (the Verification layer).
