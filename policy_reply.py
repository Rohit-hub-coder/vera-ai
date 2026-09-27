from datetime import timedelta
from composer import llm_classify_intent, compose_reply

AUTO_REPLY_PATTERNS = ["thank you for contacting", "our team will respond", "automated assistant"]
OPT_OUT_PATTERNS = ["stop messaging", "not interested", "unsubscribe", "stop sending", "cancel"]
HOSTILE_PATTERNS = ["bothering me", "useless", "spam", "hate", "angry"]
OFF_TOPIC_PATTERNS = ["gst", "tax filing"]

def classify_message(message: str) -> str:
    m = message.lower()
    if any(p in m for p in AUTO_REPLY_PATTERNS):
        return "auto_reply"
    if any(p in m for p in OPT_OUT_PATTERNS):
        return "opt_out"
    if any(p in m for p in HOSTILE_PATTERNS):
        return "hostile"
    if any(p in m for p in OFF_TOPIC_PATTERNS):
        return "off_topic"
    
    if "ok lets do it" in m or "whats next" in m or "what's next" in m or "go ahead" in m or "lets proceed" in m or "let's do it" in m or "let's proceed" in m:
        return "commit"
        
    return llm_classify_intent(message)

def nudge_body(conv) -> str:
    return "Are you there? Just wanted to follow up on my previous message."

def decide_reply(req, store):
    conv = store.conversations.setdefault(
        req.conversation_id,
        __import__("store").ConversationState(req.merchant_id, req.customer_id, None)
    )
    
    conv.history.append({"role": req.from_role, "message": req.message, "at": req.received_at})
    label = classify_message(req.message)

    if label == "auto_reply":
        store.merchant_auto_replies[req.merchant_id] = store.merchant_auto_replies.get(req.merchant_id, 0) + 1
        count = store.merchant_auto_replies[req.merchant_id]
        if count == 1:
            return {"action": "send", "body": nudge_body(conv),
                    "cta": "binary_yes_no", "rationale": "First auto-reply, gentle nudge."}
        elif count == 2:
            return {"action": "wait", "wait_seconds": 86400, "body": "", "cta": "",
                    "rationale": "Second auto-reply in a row; backing off 24h."}
        else:
            conv.status = "ended"
            return {"action": "end", "body": "", "cta": "", "rationale": "Auto-reply 3x; zero engagement, closing."}

    store.merchant_auto_replies[req.merchant_id] = 0  # reset on any real message

    if label == "opt_out":
        conv.status = "ended"
        store.suppressed_merchants[req.merchant_id] = req.received_at + timedelta(days=30)
        return {"action": "end", "body": "", "cta": "", "rationale": "Explicit opt-out; suppressing merchant 30 days."}

    if label == "hostile":
        conv.status = "ended"
        store.suppressed_merchants[req.merchant_id] = req.received_at + timedelta(days=30)
        return {"action": "end", "body": "", "cta": "", "rationale": "Hostility detected; closing without further engagement."}

    if label == "commit":
        body = compose_reply(conv, req, mode="execute")
        conv.sent_bodies.add(body.get("body", ""))
        return {"action": "send", "body": body.get("body", ""), "cta": body.get("cta", "binary_confirm_cancel"),
                "rationale": "Explicit commitment; switching from qualifying to execution."}

    if label == "off_topic":
        body = compose_reply(conv, req, mode="redirect")
        action = body.get("action", "send")
        if action == "send":
            conv.sent_bodies.add(body.get("body", ""))
        resp = {"action": action, "body": body.get("body", ""), "cta": body.get("cta", "open_ended"), "rationale": "Out-of-scope ask declined; redirected to original thread."}
        if "wait_seconds" in body: resp["wait_seconds"] = body["wait_seconds"]
        return resp

    body = compose_reply(conv, req, mode="continue")
    action = body.get("action", "send")
    if action == "send":
        conv.sent_bodies.add(body.get("body", ""))
    resp = {"action": action, "body": body.get("body", ""), "cta": body.get("cta", "open_ended"), "rationale": "Engaged reply; continuing composed thread."}
    if "wait_seconds" in body: resp["wait_seconds"] = body["wait_seconds"]
    return resp
