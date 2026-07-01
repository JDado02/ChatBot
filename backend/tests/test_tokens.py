import pytest

from app.security.tokens import issue_token, verify_token, TokenError

SECRET = "dev-secret"


def test_issue_and_verify_roundtrip():
    tok = issue_token({"tenant_id": "hotel_alpha", "sid": "s1"}, SECRET, ttl_seconds=300, now_ts=1000)
    payload = verify_token(tok, SECRET, now_ts=1000)
    assert payload["tenant_id"] == "hotel_alpha"
    assert payload["sid"] == "s1"
    assert payload["iat"] == 1000
    assert payload["exp"] == 1300


def test_expired_token_rejected():
    tok = issue_token({"sid": "s1"}, SECRET, ttl_seconds=60, now_ts=1000)
    with pytest.raises(TokenError):
        verify_token(tok, SECRET, now_ts=1061)  # oltre exp=1060


def test_valid_just_before_expiry():
    tok = issue_token({"sid": "s1"}, SECRET, ttl_seconds=60, now_ts=1000)
    assert verify_token(tok, SECRET, now_ts=1059)["sid"] == "s1"


def test_wrong_secret_rejected():
    tok = issue_token({"sid": "s1"}, SECRET, now_ts=1000)
    with pytest.raises(TokenError):
        verify_token(tok, "altro-secret", now_ts=1000)


def test_tampered_payload_rejected():
    tok = issue_token({"sid": "s1"}, SECRET, now_ts=1000)
    part, sig = tok.split(".", 1)
    tampered = part[:-1] + ("A" if part[-1] != "A" else "B") + "." + sig
    with pytest.raises(TokenError):
        verify_token(tampered, SECRET, now_ts=1000)


def test_malformed_token_rejected():
    with pytest.raises(TokenError):
        verify_token("senza-punto", SECRET, now_ts=1000)
