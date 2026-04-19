import uuid
import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.models.user import UserRole


def test_password_hash_and_verify():
    plain = "mysecurepassword123"
    hashed = hash_password(plain)

    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_hash_is_different_each_time():
    """bcrypt generates a unique salt each time."""
    plain = "samepassword"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)
    assert hash1 != hash2


def test_create_and_decode_token():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    role = UserRole.EDITOR

    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role.value,
    )

    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == role.value


def test_token_contains_expiry():
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=UserRole.VIEWER.value,
    )
    payload = decode_access_token(token)
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


def test_token_with_custom_expiry():
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=UserRole.VIEWER.value,
        expires_minutes=5,
    )
    payload = decode_access_token(token)
    assert payload["exp"] > payload["iat"]


def test_invalid_token_raises():
    from jose import JWTError
    with pytest.raises(JWTError):
        decode_access_token("this.is.not.a.valid.token")


def test_tampered_token_raises():
    from jose import JWTError
    token = create_access_token(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=UserRole.VIEWER.value,
    )
    # Tamper with the signature
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(JWTError):
        decode_access_token(tampered)
