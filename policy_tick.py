from datetime import datetime
from composer import compose
from validators import validate_action

def decide_tick(now: datetime, available_triggers: list[str], store) -> list[dict]:
    actions = []
    sent_targets = set()

    eligible = []
    for tid in available_triggers:
        if tid in store.sent_triggers:
            continue
        trig = store.get("trigger", tid)
        if not trig:
            continue
        if trig.get("expires_at"):
            exp = datetime.fromisoformat(trig["expires_at"].replace("Z", "+00:00"))
            if exp.timestamp() < now.timestamp():
                continue
        if store.is_suppressed(trig.get("suppression_key"), trig.get("merchant_id"), now):
            continue
        eligible.append((tid, trig))

    eligible.sort(key=lambda item: -item[1].get("urgency", 1))

    for tid, trig in eligible:
        cid = trig.get("customer_id") or trig.get("payload", {}).get("customer_id")
        mid = trig.get("merchant_id") or trig.get("payload", {}).get("merchant_id")
        
        # If merchant_id is missing but we have customer_id, try to resolve it from the customer context
        if not mid and cid:
            cust = store.get("customer", cid)
            if cust:
                mid = cust.get("merchant_id")
                
        if not mid:
            print(f"Skipping trigger {tid}: no merchant_id resolvable")
            continue
        
        target = (mid, cid)
        if target in sent_targets:
            continue
            
        category_slug = trig.get("payload", {}).get("category")
        if not category_slug:
            merchant_ctx = store.get("merchant", mid)
            if merchant_ctx:
                category_slug = merchant_ctx.get("category_slug")
                
        category = store.get("category", category_slug) if category_slug else None
        merchant = store.get("merchant", mid)
        customer = store.get("customer", cid) if cid else None
        
        if not merchant:
            continue

        try:
            composed = compose(category, merchant, trig, customer)
        except Exception as e:
            print(f"Composer failed for {mid}: {e}")
            continue

        params = composed.get("template_params")
        if not params or not isinstance(params, list) or len(params) == 0:
            params = [merchant.get("name", "Merchant"), "Important account update", "Reply to learn more"]
            
        raw_cta = composed.get("cta") or "open_ended"
        valid_ctas = {"open_ended", "binary_yes_no", "binary_confirm_cancel", "multi_choice_slot", "none"}
        cta = raw_cta if raw_cta in valid_ctas else "open_ended"
            
        conv_id = f"conv_{mid}_{tid}"
        action = {
            "conversation_id": conv_id,
            "merchant_id": mid,
            "customer_id": cid,
            "send_as": "merchant_on_behalf" if trig.get("scope") == "customer" else "vera",
            "trigger_id": tid,
            "template_name": f"vera_{trig.get('kind')}_v1",
            "template_params": params,
            "body": composed.get("body") or "Here is an important update regarding your account.",
            "cta": cta,
            "suppression_key": trig.get("suppression_key") or composed.get("suppression_key_suggestion") or "auto",
            "rationale": composed.get("rationale") or "composed message",
        }
        
        errors = validate_action(action, store.conversations.get(conv_id))
        if errors:
            print(f"Validation failed for {tid}: {errors}")
            continue  # fails validation -> silently skip

        actions.append(action)
        sent_targets.add(target)
        store.sent_triggers.add(tid)

    return actions
