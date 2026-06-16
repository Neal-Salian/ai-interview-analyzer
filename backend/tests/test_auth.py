"""
Fast unit tests — no DB required.
"""
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hash_and_verify():
    password = "test-password-123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_create_and_decode():
    payload = {"sub": "test@example.com"}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "test@example.com"


def test_jwt_invalid_token():
    result = decode_access_token("not-a-real-token")
    assert result is None