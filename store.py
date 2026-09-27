from datetime import datetime, timedelta

class ConversationState:
    def __init__(self, merchant_id, customer_id, trigger_id):
        self.merchant_id = merchant_id
        self.customer_id = customer_id
        self.trigger_id = trigger_id
        self.turn_number = 1
        self.history = []          # [{role, message, at}]
        self.last_bot_action = None
        self.consecutive_auto_replies = 0
        self.status = "active"     # active | waiting | ended
        self.wait_until = None
        self.sent_bodies = set()

class ContextStore:
    def __init__(self):
        self.category, self.merchant, self.customer, self.trigger = {}, {}, {}, {}
        self.conversations: dict[str, ConversationState] = {}
        self.suppressed_keys: dict[str, datetime] = {}
        self.suppressed_merchants: dict[str, datetime] = {}
        self.merchant_auto_replies: dict[str, int] = {}
        self.sent_triggers: set[str] = set()

    def upsert(self, scope, context_id, version, payload):
        store = getattr(self, scope)
        if context_id in store and store[context_id][0] >= version:
            return False, "stale_version"
        store[context_id] = (version, payload)
        return True, "accepted"

    def current_version(self, scope, context_id):
        store = getattr(self, scope)
        return store[context_id][0] if context_id in store else None

    def get(self, scope, context_id):
        store = getattr(self, scope)
        return store[context_id][1] if context_id in store else None

    def is_suppressed(self, suppression_key, merchant_id, now):
        now_ts = now.timestamp()
        if suppression_key in self.suppressed_keys and self.suppressed_keys[suppression_key].timestamp() > now_ts:
            return True
        if merchant_id in self.suppressed_merchants and self.suppressed_merchants[merchant_id].timestamp() > now_ts:
            return True
        return False
