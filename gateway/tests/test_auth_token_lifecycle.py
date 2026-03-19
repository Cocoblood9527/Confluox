import time

from gateway.auth import issue_scoped_auth_token, validate_scoped_auth_token


def test_validate_scoped_auth_token_accepts_valid_scope_and_ttl() -> None:
    secret = "gateway-secret"
    now = int(time.time())
    token = issue_scoped_auth_token(secret, scope="gateway-api", issued_at=now - 5)

    validation = validate_scoped_auth_token(
        token,
        secret=secret,
        required_scope="gateway-api",
        ttl_seconds=60,
        now_seconds=now,
    )

    assert validation.ok is True
    assert validation.error_code is None


def test_validate_scoped_auth_token_rejects_expired_tokens() -> None:
    secret = "gateway-secret"
    now = int(time.time())
    token = issue_scoped_auth_token(secret, scope="gateway-api", issued_at=now - 3600)

    validation = validate_scoped_auth_token(
        token,
        secret=secret,
        required_scope="gateway-api",
        ttl_seconds=60,
        now_seconds=now,
    )

    assert validation.ok is False
    assert validation.error_code == "auth_token_expired"


def test_validate_scoped_auth_token_rejects_wrong_scope() -> None:
    secret = "gateway-secret"
    now = int(time.time())
    token = issue_scoped_auth_token(secret, scope="plugin-api", issued_at=now)

    validation = validate_scoped_auth_token(
        token,
        secret=secret,
        required_scope="gateway-api",
        ttl_seconds=60,
        now_seconds=now,
    )

    assert validation.ok is False
    assert validation.error_code == "auth_token_scope_mismatch"
