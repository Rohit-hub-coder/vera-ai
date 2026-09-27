import json
import requests
import uuid

# We will generate synthetic triggers across the 5 categories and various trigger kinds
CATEGORIES = ["dentists", "gyms", "pharmacies", "restaurants", "salons"]
TRIGGERS = [
    "research_digest", "perf_spike", "curious_ask_due", "subscription_expiring",
    "recall_due", "festival_upcoming", "competitor_opened", "customer_lapsed_hard",
    "milestone_reached", "weather_heatwave"
]

def push_context(scope, id, data):
    from datetime import datetime
    requests.post("http://127.0.0.1:8080/v1/context", json={
        "scope": scope,
        "context_id": id,
        "version": 1,
        "delivered_at": datetime.utcnow().isoformat(),
        "payload": data
    }).raise_for_status()

def main():
    print("Generating submission.jsonl...")
    with open("submission.jsonl", "w", encoding="utf-8") as f:
        count = 1
        for cat in CATEGORIES:
            cat_id = f"c_{cat}"
            push_context("category", cat_id, {"name": cat, "voice": "Professional and helpful."})
            
            for trigger_kind in TRIGGERS[:6]:  # Generate 30 pairs (5 categories * 6 triggers = 30)
                test_id = f"test_{count:03d}"
                merch_id = f"m_{cat}_{count}"
                cust_id = f"cust_{cat}_{count}"
                trig_id = f"t_{count}"
                
                push_context("merchant", merch_id, {
                    "name": f"Test {cat.title()} Merchant",
                    "category_id": cat_id,
                    "available_slots": ["Wed 5pm", "Thu 6pm"]
                })
                
                push_context("customer", cust_id, {
                    "identity": {"name": "Priya", "language_preference": "hi-en mix"},
                    "preferences": {"language_pref": "hi-en mix"}
                })
                
                trigger_data = {
                    "trigger_id": trig_id,
                    "kind": trigger_kind,
                    "merchant_id": merch_id,
                    "scope": "customer" if trigger_kind in ["recall_due", "customer_lapsed_hard"] else "merchant",
                    "payload": {"customer_id": cust_id, "available_slots": ["Wed 5pm"]}
                }
                
                # Push trigger context
                push_context("trigger", trig_id, trigger_data)
                
                # Call /v1/tick
                from datetime import datetime
                try:
                    resp = requests.post("http://127.0.0.1:8080/v1/tick", json={
                        "now": datetime.utcnow().isoformat(),
                        "available_triggers": [trig_id]
                    }, timeout=10)
                    resp_json = resp.json()
                    actions = resp_json.get("actions", [])
                    if actions:
                        action = actions[0]
                        f.write(json.dumps({
                            "test_id": test_id,
                            "body": action.get("body", ""),
                            "cta": action.get("cta", "open_ended"),
                            "send_as": action.get("send_as", "vera"),
                            "suppression_key": action.get("suppression_key", "auto"),
                            "rationale": action.get("rationale", "Generated action")
                        }) + "\n")
                    else:
                        print(f"Empty action for {test_id}")
                except Exception as e:
                    print(f"Failed {test_id}: {e}")
                
                count += 1

if __name__ == "__main__":
    main()
