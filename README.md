# Vera Proactive Engagement Bot

## Approach

We implemented the bot using a 3-layer architecture:

1. Operational Layer
   - FastAPI web server
   - `/v1/context`
   - `/v1/tick`
   - `/v1/reply`
   - `/v1/healthz`
   - `/v1/metadata`

2. Policy Layer
   - Handles trigger decisions
   - Anti-repetition logic
   - Deterministic reply handling
   - Opt-out and off-topic routing

3. Composition Layer
   - Gemini 2.5 Flash
   - Prompt-based message generation
   - Local fallback when the model/API is unavailable

## Reliability

The bot includes local fallback responses so that API failures or rate limits do not automatically result in HTTP 500 errors.

## Data

Context is kept in memory and processed through the FastAPI endpoints.
