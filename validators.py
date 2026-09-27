import re
URL_RE = re.compile(r"https?://")

def validate_action(action: dict, conv: "ConversationState | None") -> list[str]:
    errors = []
    required = ["conversation_id", "merchant_id", "send_as", "trigger_id",
                "template_name", "template_params", "body", "cta",
                "suppression_key", "rationale"]
    for field in required:
        val = action.get(field)
        if val is None or (val == "" and field != "template_params"):
            errors.append(f"missing_field:{field}")
    if URL_RE.search(action.get("body", "")):
        errors.append("url_in_body")
    if conv and action.get("body") in conv.sent_bodies:
        errors.append("repeated_body")
    return errors
