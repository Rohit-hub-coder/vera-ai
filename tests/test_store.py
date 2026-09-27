from store import ContextStore

def test_idempotent_version_rejected():
    s = ContextStore()
    ok, _ = s.upsert("merchant", "m1", 1, {"a": 1})
    assert ok
    ok, reason = s.upsert("merchant", "m1", 1, {"a": 2})
    assert not ok and reason == "stale_version"

def test_version_bump_replaces():
    s = ContextStore()
    s.upsert("merchant", "m1", 1, {"a": 1})
    ok, _ = s.upsert("merchant", "m1", 2, {"a": 2})
    assert ok
    assert s.get("merchant", "m1") == {"a": 2}
