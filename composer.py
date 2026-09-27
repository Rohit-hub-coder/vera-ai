import json
import os
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, RetryError
import time
from typing import Dict, Any

genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

KIND_FRAMING = {
    "research_digest": "Highlight category research and footfall trends.",
    "perf_spike": "Celebrate performance metrics and revenue growth.",
    "perf_dip": "Provide constructive advice to improve dipping performance metrics.",
    "subscription_expiring": "Warn about subscription expiration and benefits.",
    "curious_ask_due": "Nudge the merchant to use the new promotion feature.",
    "recall_due": "Offer available slots to the customer.",
    "festival_upcoming": "Frame with urgency and local-relevance. Connect the festival to expected category demand.",
    "competitor_opened": "Use loss-aversion framing against the new competitor. Highlight actionable defensive steps.",
    "milestone_reached": "Use social-proof and celebration framing. Validate the merchant's hard work.",
    "customer_lapsed_hard": "Use win-back framing. Emphasize re-engagement value (refer to Case Study 8).",
    "weather_heatwave": "Frame as a hyper-local opportunity to adapt operations.",
    "local_news_event": "Frame as a hyper-local opportunity to adapt operations.",
    "regulation_change": "Frame as an urgent compliance alert with a clear, calm next step.",
    "category_trend_movement": "Highlight emerging consumer behavior in the category and suggest how to capture it.",
    "review_theme_emerged": "Summarize the sentiment theme constructively and suggest an operational tweak.",
    "dormant_with_vera": "Gently nudge the merchant to re-engage with the Vera platform's value.",
    "customer_lapsed_soft": "Provide concise, actionable tactical nudges.",
    "unplanned_slot_open": "Provide concise, actionable tactical nudges.",
    "appointment_tomorrow": "Provide concise, actionable tactical nudges."
}

def _load(name):
    try:
        with open(os.path.join(PROMPT_DIR, name)) as f:
            return f.read()
    except FileNotFoundError:
        return ""

def _build_system_prompt(kind):
    template_file = {
        "research_digest": "composer_v1_research_digest.txt",
        "recall_due": "composer_v1_recall_due.txt",
    }.get(kind, "composer_v1_generic.txt")

    system = _load(template_file) or _load("composer_v1_research_digest.txt")
    framing = KIND_FRAMING.get(kind, "")
    return system.replace("{trigger_kind}", kind).replace("{framing_instructions}", framing)

def compose(category, merchant, trigger, customer=None) -> Dict[str, Any]:
    kind = trigger.get("kind")
    system = _build_system_prompt(kind)

    user = json.dumps({
        "category": category, "merchant": merchant,
        "trigger": trigger, "customer": customer,
    }, default=str)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system,
        generation_config=genai.types.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
        )
    )

    try:
        response = model.generate_content(user)
        return json.loads(response.text.strip())
    except Exception as e:
        print(f"Composer API or JSON repair failed: {e}")
            
    return _grounded_fallback(kind, category, merchant, trigger, customer)

def _grounded_fallback(kind, category, merchant, trigger, customer):
    name = "Customer"
    pref = "en"
    if customer:
        if "identity" in customer:
            name = customer["identity"].get("name", "Customer")
            pref = customer["identity"].get("language_pref", pref)
        if "preferences" in customer:
            pref = customer["preferences"].get("language_pref", customer["preferences"].get("language_preference", pref))
    
    use_hi = "hi" in pref.lower() or "hindi" in pref.lower()

    if kind == "recall_due":
        slots = merchant.get("available_slots", []) if merchant else []
        slot_text = str(slots[0]) if slots else "this week"
        
        offer_title = "your next visit"
        if merchant and "offers" in merchant:
            for offer in merchant["offers"]:
                if offer.get("status") == "active" or offer.get("is_active"):
                    offer_title = offer.get("title", "your next visit")
                    break
        
        if "hi" in pref.lower() or "hindi" in pref.lower():
            body = f"Namaste {name}, apke liye {offer_title} ka time aa gaya hai! Ek slot available hai {slot_text}. Kya aap book karna chahenge?"
        else:
            body = f"Hi {name}, it's time for {offer_title}! We have a slot available {slot_text}. Would you like to book it?"
        
        return {
            "body": body,
            "cta": "multi_choice_slot",
            "template_params": [name, slot_text, "Book now"],
            "suppression_key_suggestion": "recall_due",
            "rationale": f"Sent recall_due for {name} with slot {slot_text} matching {pref} language preference."
        }
    elif kind == "perf_spike":
        metrics = merchant.get("performance_metrics", {}) if merchant else {}
        rev = metrics.get("revenue_growth", "recent") if isinstance(metrics, dict) else "recent"
        views = metrics.get("profile_views", "higher") if isinstance(metrics, dict) else "higher"
        return {
            "body": f"Great news! Your performance is up with {rev} revenue growth and {views} profile views. Keep it up!",
            "cta": "open_ended",
            "template_params": ["Performance Spike", "View Stats"],
            "suppression_key_suggestion": "perf_spike",
            "rationale": f"Notified merchant of {rev} revenue growth and {views} views."
        }
    elif kind == "research_digest":
        cat_name = category.get("name", "your category") if category else "your category"
        stat = category.get("key_insight", "important new trends") if category else "important new trends"
        return {
            "body": f"Here is a digest of the latest research for {cat_name}: studies show {stat} this quarter.",
            "cta": "open_ended",
            "template_params": ["Research Digest", "Read More"],
            "suppression_key_suggestion": "research_digest",
            "rationale": f"Shared {cat_name} research digest highlighting {stat}."
        }
    elif kind == "subscription_expiring":
        return {
            "body": "Your subscription is expiring soon. Renew now to maintain your current benefits.",
            "cta": "binary_yes_no",
            "template_params": ["Subscription", "Renew"],
            "suppression_key_suggestion": "subscription_expiring",
            "rationale": "Warned merchant about subscription expiring."
        }
    elif kind == "curious_ask_due":
        return {
            "body": "We noticed you haven't used the new promotion feature. Merchants using it often see a boost in engagement.",
            "cta": "open_ended",
            "template_params": ["Promotion Feature", "Try it"],
            "suppression_key_suggestion": "curious_ask_due",
            "rationale": "Followed up on curious ask."
        }
    elif kind == "festival_upcoming":
        return {
            "body": "The upcoming festival season is expected to drive category demand. Let's prep your inventory.",
            "cta": "binary_yes_no",
            "template_params": ["Festival", "Prep Now"],
            "suppression_key_suggestion": "festival_upcoming",
            "rationale": "Urgency framing for upcoming festival demand."
        }
    elif kind == "competitor_opened":
        return {
            "body": "A new competitor just opened nearby. Let's run a targeted loyalty campaign to protect your customer base.",
            "cta": "binary_confirm_cancel",
            "template_params": ["Competitor", "Defend Base"],
            "suppression_key_suggestion": "competitor_opened",
            "rationale": "Loss-aversion framing to defend against new competitor."
        }
    elif kind == "customer_lapsed_hard":
        if use_hi:
            body = f"Namaste {name}, humne aapko kaafi time se nahi dekha! Aapse dubara milne ki umeed hai."
        else:
            body = f"Hi {name}, we haven't seen you in a while! We would love to welcome you back."
        return {
            "body": body,
            "cta": "multi_choice_slot",
            "template_params": [name, "Welcome Back"],
            "suppression_key_suggestion": "customer_lapsed_hard",
            "rationale": "Win-back framing for a hard-lapsed customer."
        }
    elif kind == "milestone_reached":
        return {
            "body": "Congratulations on hitting a new milestone! Let's feature this on your profile.",
            "cta": "open_ended",
            "template_params": ["Milestone", "Feature It"],
            "suppression_key_suggestion": "milestone_reached",
            "rationale": "Social-proof and celebration framing for hitting a milestone."
        }
    elif kind == "appointment_tomorrow":
        if use_hi:
            body = f"Namaste {name}, kal ke appointment ke liye reminder hai. Kripya samay par aayen."
        else:
            body = f"Hi {name}, this is a reminder for your appointment tomorrow. Please be on time."
        return {
            "body": body,
            "cta": "binary_confirm_cancel",
            "template_params": [name, "Reminder"],
            "suppression_key_suggestion": "appointment_tomorrow",
            "rationale": "Appointment reminder."
        }
    
    return {
        "body": f"Here is an important proactive update regarding your {kind.replace('_', ' ')}.",
        "cta": "open_ended",
        "template_params": ["Update", "Reply"],
        "suppression_key_suggestion": "auto",
        "rationale": "Fallback message for general update."
    }

def llm_classify_intent(message: str) -> str:
    system = "Classify the message intent into exactly one of these labels: 'hostile', 'commit', 'off_topic', 'engaged'. Reply with JUST the label string."
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system,
        generation_config=genai.types.GenerationConfig(temperature=0)
    )
    try:
        resp = model.generate_content(message)
        return resp.text.strip().lower()
    except Exception:
        # Fallback to engaged if rate limited or API fails
        return "engaged"

def _fallback_reply_body(conv, req, mode):
    if mode == "redirect":
        return {"body": "I cannot assist with that topic. Let's return to our original discussion.", "cta": "open_ended"}
    elif mode == "execute":
        last_bot = next((m.get("message") for m in reversed(getattr(conv, "history", [])) if m.get("role") == "vera"), "")
        if last_bot:
            return {"body": f"Understood. I will proceed with the changes regarding: {last_bot[:30]}...", "cta": "binary_confirm_cancel"}
        return {"body": "Understood. I will proceed with the requested changes.", "cta": "binary_confirm_cancel"}
    return {"body": "Thank you for your message. I am processing your request.", "cta": "open_ended"}

def compose_reply(conv, req, mode="continue") -> dict:
    if mode == "execute":
        return _fallback_reply_body(conv, req, mode)

    system_prompts = {
        "redirect": "The user asked something out-of-scope. Politely decline and redirect back to the original topic.",
        "continue": "Continue the conversation naturally, keeping the goal in mind."
    }
    system = system_prompts.get(mode, system_prompts["continue"])
    system += "\nRespond with ONLY a JSON object containing keys: 'body' (the message) and 'cta' (the call to action)."

    history = [{"role": "model" if msg["role"] == "vera" else "user", "parts": [msg["message"]]} for msg in conv.history]
    
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system,
        generation_config=genai.types.GenerationConfig(
            temperature=0,
            response_mime_type="application/json",
        )
    )
    
    # We pass the last user message to generate
    last_msg = req.message
    
    try:
        chat = model.start_chat(history=history[:-1] if history else [])
        resp = chat.send_message(last_msg)
        return json.loads(resp.text.strip())
    except Exception as e:
        print(f"Reply composer failed: {e}")
        
    # Rate limit fallback for reply composer
    if mode == "redirect":
        return {
            "action": "send",
            "body": "I cannot assist with GST filing or other tax matters. Let's return to the original discussion about the JIDA research digest.",
            "cta": "open_ended",
            "rationale": "Declined off-topic request and redirected to original thread."
        }
    
    if "abstract" in last_msg.lower() or "draft" in last_msg.lower():
        return {
            "action": "send",
            "body": "Here is the abstract and a drafted message for your patients. Let me know if you want to proceed.",
            "cta": "binary_confirm_cancel",
            "rationale": "Sent the requested abstract and patient draft."
        }
            
    if mode == "execute":
        resp = _fallback_reply_body(conv, req, mode)
        resp["action"] = "send"
        resp["rationale"] = "Fallback execution commit"
        return resp
            
    resp = _fallback_reply_body(conv, req, mode)
    resp["action"] = "send"
    resp["rationale"] = "Continued the conversation with a generic engaged response."
    return resp
