"""
HMAC-SHA256 Signature Utilities for Webhook Security

This module provides functions for generating and verifying HMAC-SHA256
signatures for webhook payloads, following the GitHub/Stripe webhook
signature pattern.

The signature format is: "sha256={hex_digest}"

Example usage:
    >>> from src.core.security.hmac_signature import generate_signature, verify_signature
    >>> payload = {"event": "instance.started", "data": {"instance_id": "123"}}
    >>> secret = "my_webhook_secret"
    >>> signature = generate_signature(payload, secret)
    >>> verify_signature(payload, secret, signature)
    True
"""
import hmac
import hashlib
import json
from typing import Union, Dict, Any


# Signature prefix following GitHub/Stripe convention
SIGNATURE_PREFIX = "sha256="


def generate_signature(
    payload: Union[Dict[str, Any], str, bytes],
    secret: str
) -> str:
    """
    Generate an HMAC-SHA256 signature for a webhook payload.

    The signature is computed using the secret key and a JSON-serialized
    (with sorted keys for consistency) version of the payload. This ensures
    that the same payload always produces the same signature regardless of
    key ordering in dictionaries.

    Args:
        payload: The webhook payload. Can be:
            - dict: Will be JSON-serialized with sorted keys
            - str: Will be used as-is (assumed to be JSON string)
            - bytes: Will be used as-is
        secret: The webhook secret key for signing

    Returns:
        Signature string in format "sha256={hex_digest}"

    Raises:
        TypeError: If payload is not dict, str, or bytes
        ValueError: If secret is empty

    Example:
        >>> generate_signature({"test": "data"}, "secret123")
        'sha256=...'
    """
    if not secret:
        raise ValueError("Secret key cannot be empty")

    # Convert payload to bytes
    if isinstance(payload, dict):
        # Sort keys for consistent signature generation
        payload_bytes = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    elif isinstance(payload, str):
        payload_bytes = payload.encode('utf-8')
    elif isinstance(payload, bytes):
        payload_bytes = payload
    else:
        raise TypeError(f"Payload must be dict, str, or bytes, not {type(payload).__name__}")

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()

    return f"{SIGNATURE_PREFIX}{signature}"


def verify_signature(
    payload: Union[Dict[str, Any], str, bytes],
    secret: str,
    signature: str
) -> bool:
    """
    Verify an HMAC-SHA256 signature for a webhook payload.

    This function uses `hmac.compare_digest()` to perform a constant-time
    comparison, preventing timing attacks that could leak signature information.

    Args:
        payload: The webhook payload. Can be:
            - dict: Will be JSON-serialized with sorted keys
            - str: Will be used as-is (assumed to be JSON string)
            - bytes: Will be used as-is
        secret: The webhook secret key used for signing
        signature: The signature to verify (format: "sha256={hex_digest}")

    Returns:
        True if the signature is valid, False otherwise

    Example:
        >>> payload = {"test": "data"}
        >>> secret = "secret123"
        >>> signature = generate_signature(payload, secret)
        >>> verify_signature(payload, secret, signature)
        True
        >>> verify_signature(payload, "wrong_secret", signature)
        False
    """
    if not secret or not signature:
        return False

    try:
        # Generate expected signature
        expected_signature = generate_signature(payload, secret)

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)
    except (ValueError, TypeError):
        return False


def extract_signature_from_header(header_value: str) -> str:
    """
    Extract the signature from a webhook signature header value.

    Some webhook systems may include additional metadata in the signature
    header (e.g., timestamp). This function extracts just the sha256 signature.

    Args:
        header_value: The full header value (e.g., "sha256=abc123" or "t=123,sha256=abc123")

    Returns:
        The signature portion (e.g., "sha256=abc123")

    Example:
        >>> extract_signature_from_header("sha256=abc123def456")
        'sha256=abc123def456'
        >>> extract_signature_from_header("t=1234567890,sha256=abc123def456")
        'sha256=abc123def456'
    """
    if not header_value:
        return ""

    # Handle comma-separated header values (Stripe-style)
    parts = header_value.split(',')
    for part in parts:
        part = part.strip()
        if part.startswith(SIGNATURE_PREFIX):
            return part

    # If no prefix found but header starts with sha256=, return as-is
    if header_value.startswith(SIGNATURE_PREFIX):
        return header_value

    return ""
