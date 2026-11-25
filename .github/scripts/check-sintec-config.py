#!/usr/bin/env python3
"""Validate corporate build settings without printing their values."""
import base64
import binascii
import os
import sys


def validate(environ):
    address = environ.get("SINTEC_SERVER_ADDRESS", "")
    key = environ.get("SINTEC_SERVER_PUBLIC_KEY", "")
    if not address or address != address.strip() or any(c.isspace() for c in address):
        raise ValueError("Set SINTEC_SERVER_ADDRESS to the server host or host:port.")
    if any(c in address for c in "/\\@?#"):
        raise ValueError("SINTEC_SERVER_ADDRESS must be a host or host:port, not a URL.")
    try:
        public_key = base64.b64decode(key, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("SINTEC_SERVER_PUBLIC_KEY must be a base64 public key.") from None
    if len(public_key) != 32:
        raise ValueError("SINTEC_SERVER_PUBLIC_KEY must encode 32 bytes; do not use a private key.")


if __name__ == "__main__":
    try:
        validate(os.environ)
    except ValueError as error:
        print(f"::error::{error}", file=sys.stderr)
        sys.exit(1)
    print("Sintec.RD build settings validated; values are not logged.")
