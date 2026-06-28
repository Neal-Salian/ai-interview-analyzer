import pytest
from app.core.zoom_crypto import encrypt_zoom_token, decrypt_zoom_token

def test_encryption_decryption():
    token = "test_token_123_abc"
    encrypted = encrypt_zoom_token(token)
    assert encrypted != token
    assert isinstance(encrypted, str)
    
    decrypted = decrypt_zoom_token(encrypted)
    assert decrypted == token

def test_decrypt_invalid_token():
    with pytest.raises(ValueError, match="Invalid or corrupted encrypted Zoom token"):
        decrypt_zoom_token("invalid_base64_string_that_fails_fernet")
