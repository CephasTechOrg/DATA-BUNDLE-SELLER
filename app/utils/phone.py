"""Ghana phone number normalization for ResellerXpress (expects local 0XXXXXXXXX)."""
import re


def normalize_ghana_phone(raw: str) -> str:
    """
    Normalise a Ghana phone number to local format: 0XXXXXXXXX (10 digits).

    Accepts: 0551234567, 233551234567, +233551234567, and numbers with spaces/dashes.
    If the input can't be confidently normalised, the digits-only value is returned
    so the provider can reject it (rather than us guessing wrong).
    """
    if not raw:
        return ""
    digits = re.sub(r"\D", "", str(raw))  # strip +, spaces, dashes, etc.

    # 233XXXXXXXXX (12 digits) -> 0XXXXXXXXX
    if digits.startswith("233") and len(digits) == 12:
        return "0" + digits[3:]
    # 0XXXXXXXXX (10 digits) -> as-is
    if digits.startswith("0") and len(digits) == 10:
        return digits
    # XXXXXXXXX (9 digits, missing leading 0) -> prepend 0
    if len(digits) == 9:
        return "0" + digits
    return digits
