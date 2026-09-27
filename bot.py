from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from datetime import datetime
from models import ContextPush, TickRequest, TickResponse, ReplyRequest, ReplyResponse
from store import ContextStore

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": exc.errors()})

store = ContextStore()
START = datetime.utcnow()

import time

@app.get("/v1/healthz")
def healthz():
    t0 = time.perf_counter()
    resp = {
        "status": "ok",
        "uptime_seconds": int((datetime.utcnow() - START).total_seconds()),
        "contexts_loaded": {
            "category": len(store.category),
            "merchant": len(store.merchant),
            "customer": len(store.customer),
            "trigger": len(store.trigger),
        },
    }
    print(f"healthz internal logic took: {(time.perf_counter() - t0) * 1000:.2f}ms")
    return resp

@app.get("/v1/debug_store")
def debug_store():
    return {
        "merchants": list(store.merchant.keys()),
        "triggers": {k: v[1].get("merchant_id") for k, v in store.trigger.items()}
    }

@app.get("/v1/metadata")
def metadata():
    return {
        "team_name": "Your Team",
        "team_members": ["You"],
        "model": "claude-sonnet-4-6",
        "approach": "single-prompt composer with dispatch by trigger.kind",
        "contact_email": "you@example.com",
        "version": "0.1.0",
        "submitted_at": datetime.utcnow().isoformat(),
    }

@app.post("/v1/context")
def push_context(ctx: ContextPush):
    ok, reason = store.upsert(ctx.scope, ctx.context_id, ctx.version, ctx.payload)
    if not ok:
        return JSONResponse(status_code=409, content={
            "accepted": False, "reason": reason,
            "current_version": store.current_version(ctx.scope, ctx.context_id),
        })
    return {"accepted": True, "ack_id": f"ack_{ctx.context_id}_v{ctx.version}",
            "stored_at": datetime.utcnow().isoformat()}

from policy_tick import decide_tick

@app.post("/v1/tick", response_model=TickResponse)
def tick(req: TickRequest):
    actions = decide_tick(req.now, req.available_triggers, store)
    return TickResponse(actions=actions)

from policy_reply import decide_reply

@app.post("/v1/reply", response_model=ReplyResponse)
def reply(req: ReplyRequest):
    res = decide_reply(req, store)
    return ReplyResponse(
        action=res["action"],
        body=res.get("body"),
        cta=res.get("cta"),
        wait_seconds=res.get("wait_seconds"),
        rationale=res.get("rationale")
    )
