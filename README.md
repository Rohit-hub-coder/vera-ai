<<<<<<< HEAD
# Vera Proactive Engagement Bot
## Approach
We implemented the bot strictly following the Challenge design documentation, establishing a 3-layer architecture:
1. **Operational Layer**: Fast FastAPI web server, handling in-memory Context push (`/v1/context`) with version validation and idempotency via Python data classes. We strictly observed a sub-30ms latency for operational responses.
2. **Policy Layer**: `policy_tick` checks constraints (anti-repetition via a sent-trigger hash set) and handles formatting. `policy_reply` uses regex for deterministic auto-reply, opt-out, and hostile pattern classification, defaulting to the LLM for remaining intent mapping.
3. **Composition Layer**: A unified generative LLM (Gemini 2.5 Flash) handles the `compose` logic. We map the generic 4-context architecture (Category, Merchant, Customer, Trigger) directly into a standardized prompt system.

## Tradeoffs
1. **Local vs API Rate Limits**: Due to free-tier Gemini API limitations (15 RPM), the bot implements an intelligent, real-data local fallback that dynamically injects parameters (e.g. `customer["preferences"]["language_pref"]`) when rate limited. This guarantees high reliability without blocking the server or throwing 500s.
2. **Local Classifier over LLM Catch-alls**: We built a pre-filter classifier using explicit text heuristics (`AUTO_REPLY`, `OPT_OUT`, `OFF_TOPIC`) to aggressively route away from the LLM for clearly deterministic paths. This speeds up latency and saves quota.
3. **Single LLM call**: We reduced the number of LLM calls to exactly ONE per composition, rather than chaining (e.g., classifying, then summarizing, then generating).

## Missing Context
The output quality could be vastly improved with:
1. **Past Merchant Conversions**: If context included historical conversion rates for specific offers, Vera could recommend them more confidently.
2. **Channel Specifics**: Knowing if the communication is via WhatsApp vs Email could allow the LLM to format with bolding/emojis accordingly.
=======
# vera-ai
>>>>>>> e1af4ae054242f4d03034e00beb798c5b1aebe89
