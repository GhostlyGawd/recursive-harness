from agentops.redaction import Redactor, contains_unredacted_secret


def test_sensitive_keys_masked():
    r = Redactor()
    out, tags = r.redact({"user": "alice", "password": "hunter2", "nested": {"api_key": "xyz"}})
    assert out["user"] == "alice"
    assert out["password"] == "***REDACTED***"
    assert out["nested"]["api_key"] == "***REDACTED***"
    assert "key:password" in tags and "key:api_key" in tags


def test_patterns_masked_in_strings():
    r = Redactor()
    out, tags = r.redact("token is sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345 ok")
    assert "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345" not in out
    assert any(t.startswith("pattern:") for t in tags)


def test_aws_and_jwt_and_private_key():
    r = Redactor()
    o1, _ = r.redact("AKIAIOSFODNN7EXAMPLE")
    o2, _ = r.redact("eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcDEF123456")
    o3, _ = r.redact("-----BEGIN RSA PRIVATE KEY-----")
    assert "AKIA" not in o1 and "eyJ" not in o2 and "PRIVATE KEY" not in o3


def test_deep_list_redaction():
    r = Redactor()
    out, _ = r.redact({"items": [{"secret": "s1"}, {"ok": "v"}]})
    assert out["items"][0]["secret"] == "***REDACTED***"
    assert out["items"][1]["ok"] == "v"


def test_disabled_redactor_passes_through():
    r = Redactor(enabled=False)
    out, tags = r.redact({"password": "hunter2"})
    assert out["password"] == "hunter2" and tags == []


def test_contains_unredacted_secret_flags_credentials_not_plain_email():
    assert contains_unredacted_secret("sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ012345")
    assert contains_unredacted_secret({"k": "AKIAIOSFODNN7EXAMPLE"})
    assert not contains_unredacted_secret("contact me at jane@example.com")
    assert not contains_unredacted_secret("just some normal text")
