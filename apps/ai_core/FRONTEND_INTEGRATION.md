# AI Governance — Frontend / Client Integration Guide (Batch 6)

All seven AI features are exposed under `/api/v1/ai/` and require an
**authenticated** session (DRF `IsAuthenticated`). Successful responses are
shaped as `GatewayResponse.to_dict()` plus one feature-specific payload key.

## Endpoint summary

| Feature              | Method | URL                              | Service kwargs (required in bold)   |
|----------------------|--------|----------------------------------|-------------------------------------|
| Feature catalog      | GET    | `/api/v1/ai/features/`           | —                                   |
| Doubt Solver         | POST   | `/api/v1/ai/doubt-solver/`       | **question**, subject, topic, grade |
| Study Planner        | POST   | `/api/v1/ai/study-planner/`      | **goal**, exam_date, current_level, subjects[], hours_per_day |
| Practice Quiz        | POST   | `/api/v1/ai/practice-quiz/`      | **subject**, topic, difficulty, count, question_types[] |
| Performance Insights | POST   | `/api/v1/ai/performance-insights/` | **student_summary{}**, period     |
| Learning Path        | POST   | `/api/v1/ai/learning-path/`      | **target**, current_level, duration_weeks, persist |
| Adaptive Learning    | POST   | `/api/v1/ai/adaptive-learning/`  | **recent_performance{}**, current_topic |
| Exam Result Planning | POST   | `/api/v1/ai/exam-result-planning/` | **exam_name**, **scores{}**, target_score, weak_topics[] |
| Feedback             | POST   | `/api/v1/ai/feedback/`           | **request_id**, **verdict**, rating, comment |
| My data export       | GET    | `/api/v1/ai/me/export/`          | —                                   |
| My data erasure      | DELETE | `/api/v1/ai/me/erase/`           | —                                   |

## Standard response envelope

```jsonc
{
  "request_id": "9d1c…",          // pass back to /feedback/
  "feature_code": "DOUBT_SOLVER",
  "text": "...",                  // raw model text
  "status": "SUCCESS",
  "provider_name": "Mock",
  "model_name": "mock-gpt",
  "input_tokens": 32,
  "output_tokens": 88,
  "total_tokens": 120,
  "cost_usd": 0.000264,
  "latency_ms": 12,
  "fallback_used": false,
  "flagged": false,

  // feature-specific extras (one of):
  "answer": "...",          // doubt-solver
  "plan_text": "...",       // study-planner / exam-result-planning
  "questions": [...],       // practice-quiz
  "insights": "...",        // performance-insights
  "path_text": "...",       // learning-path
  "recommendation": "..."   // adaptive-learning
}
```

## Error envelope

When the gateway rejects a request, the response body is the dict from
`AIGatewayError.to_dict()`:

```json
{ "error": "rate_limited", "message": "Rate limit exceeded", "retry_after": 42 }
```

HTTP status codes: 400 (safety), 403 (feature disabled), 429 (rate-limit /
budget), 502 (upstream), 503 (no provider available).

## React hook example

```ts
// useAi.ts
export async function callAI<T = any>(path: string, payload: any): Promise<T> {
  const res = await fetch(`/api/v1/ai/${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrf() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export const askDoubt = (question: string) =>
  callAI("doubt-solver/", { question });

export const submitFeedback = (request_id: string, verdict: "UP" | "DOWN") =>
  callAI("feedback/", { request_id, verdict });
```

## Compliance notes for client integrators

* Inputs are scanned for PII, prompt-injection, profanity before reaching
  the model. PII is redacted before being persisted to the audit log.
* During locked exams (`Assessment.lock_ai_tools=True`) the gateway returns
  **400 `safety_blocked`** with `reason="exam_lockdown"`.
* All requests are logged to `AIUsageLog` + `AIAuditLog`. Users can fetch
  their full history via `/me/export/` and erase it via `/me/erase/`.
* Per-feature limits (rate, daily quota, monthly tokens, monthly cost)
  are configured by tenant admins in **Admin → AI Governance**.
