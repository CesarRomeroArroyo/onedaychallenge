# ClearCSV development rules

- ClearCSV is a local MVP for the One Day Build Challenge.
- Preserve uploaded CSV values as text. The original dataset is immutable.
- Deterministic rules identify verifiable issues; AI suggestions always require human review.
- Never log CSV contents, prompts containing data, full provider responses, or secrets.
- OpenAI access stays in the backend. Never expose `OPENAI_API_KEY` through Vite variables.
- Keep the single-process in-memory scope, 60-minute TTL, and dataset limits documented.
- Validate changes with the commands documented in `docs/plan.md` and update the plan with real results.
