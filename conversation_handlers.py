def respond(state, merchant_message: str) -> dict:
    """
    Given the conversation so far + the merchant's latest message, produce the reply.
    This acts as a standalone facade into our state machine in policy_reply.py.
    """
    from policy_reply import decide_reply
    
    class MockReq:
        def __init__(self):
            from datetime import datetime, timezone
            self.conversation_id = getattr(state, "conversation_id", "conv_1")
            self.merchant_id = getattr(state, "merchant_id", "m_1")
            self.customer_id = getattr(state, "customer_id", None)
            self.from_role = "merchant"
            self.message = merchant_message
            self.received_at = datetime.now(timezone.utc)
            self.turn_number = len(getattr(state, "history", [])) + 1
            
    class MockStore:
        def __init__(self):
            self.conversations = {}
            self.merchant_auto_replies = {}
            self.suppressed_merchants = {}
            
    # Use a module-level store so it persists across calls in the test
    if not hasattr(respond, "_store"):
        respond._store = MockStore()
        
    respond._store.conversations[getattr(state, "conversation_id", "conv_1")] = state
            
    return decide_reply(MockReq(), respond._store)
