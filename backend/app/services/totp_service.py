import base64
import io
import pyotp
import qrcode
from app.core.config import get_settings

settings = get_settings()


def generate_totp_secret() -> str:
    """Generate a new TOTP secret for a user."""
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    """Get the otpauth URI for QR code generation."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=email,
        issuer_name=settings.totp_issuer,
    )


def generate_qr_code_base64(secret: str, email: str) -> str:
    """
    Generate a QR code image as a base64 string.
    The frontend renders this as <img src="data:image/png;base64,...">
    """
    uri = get_totp_uri(secret, email)
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    """
    Verify a 6-digit TOTP code against the secret.
    Allows 1 window of drift (30 seconds either side).
    """
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)
