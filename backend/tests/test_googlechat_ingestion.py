"""Google Chat's bearer token is a Google-signed OIDC token — unlike GitHub's HMAC or
Slack's v0= signing, we can't fabricate a valid one ourselves to test against a real
verifier. These tests monkeypatch the google-auth library call to exercise our own
wrapper logic (missing token, unconfigured audience, verification failure, issuer check)
without needing network access to Google or a real signed token.
"""

from app.ingestion import googlechat


def test_missing_token_is_rejected():
    assert googlechat.verify_google_chat_request(None) is False


def test_missing_audience_config_is_rejected(monkeypatch):
    monkeypatch.setattr(googlechat, "GOOGLE_CHAT_AUDIENCE", "")
    assert googlechat.verify_google_chat_request("some-token") is False


def test_valid_token_from_the_chat_issuer_is_accepted(monkeypatch):
    monkeypatch.setattr(googlechat, "GOOGLE_CHAT_AUDIENCE", "https://example.com/events/googlechat")
    monkeypatch.setattr(googlechat.id_token, "verify_oauth2_token", lambda token, req, aud: {"email": googlechat.CHAT_ISSUER_EMAIL})
    assert googlechat.verify_google_chat_request("valid-token") is True


def test_token_from_a_different_issuer_is_rejected(monkeypatch):
    monkeypatch.setattr(googlechat, "GOOGLE_CHAT_AUDIENCE", "https://example.com/events/googlechat")
    monkeypatch.setattr(googlechat.id_token, "verify_oauth2_token", lambda token, req, aud: {"email": "someone-else@example.com"})
    assert googlechat.verify_google_chat_request("valid-but-wrong-issuer") is False


def test_verification_failure_is_rejected_not_raised(monkeypatch):
    monkeypatch.setattr(googlechat, "GOOGLE_CHAT_AUDIENCE", "https://example.com/events/googlechat")

    def _raise(token, req, aud):
        raise ValueError("invalid token")

    monkeypatch.setattr(googlechat.id_token, "verify_oauth2_token", _raise)
    assert googlechat.verify_google_chat_request("tampered-or-expired") is False
