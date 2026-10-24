"""Demo-grade authentication for the DataMon portal.

This is honest about what it is: a local, trusted-file hackathon login, NOT
production SSO. It does the sensible things a login should — passwords are stored
only as salted PBKDF2-HMAC-SHA256 hashes (never plaintext), verified in constant
time; repeated failures lock the account for a cooldown; and a session expires
after an idle timeout. It deliberately does NOT provide TLS, a real user store,
or protection against someone who can edit the Streamlit session state on their
own machine. See SECURITY.md for the controls a networked deployment would need.

The two demo accounts and their credentials are intentionally public — the
hackathon rules require working login credentials in the testing instructions
(see TESTING.md). Only the salted hashes live here; the plaintext does not.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Dict, Optional

PBKDF2_ROUNDS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 60
SESSION_IDLE_TIMEOUT = 30 * 60  # 30 minutes


@dataclass(frozen=True)
class Credential:
    role: str
    salt_hex: str
    hash_hex: str


# Salted PBKDF2-HMAC-SHA256 digests. Plaintext is documented in TESTING.md only.
CREDENTIALS: Dict[str, Credential] = {
    "programmer": Credential(
        role="programmer",
        salt_hex="42ce8b355b0f0501015fe40417fca8a0",
        hash_hex="56764b6c2b09a99313519fbb8e9525bef3689598b73e4c4a67f0675b3d44fe12",
    ),
    "judge": Credential(
        role="judge",
        salt_hex="0cf95f0607f64abc333363df813d2993",
        hash_hex="25a804eeab35718c7c5acc079c7e3dc423170c13d840ffb2a070a9c6c3f920f9",
    ),
}


def _hash(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return dk.hex()


def verify_password(username: str, password: str) -> Optional[str]:
    """Return the role on a correct match, else None. Constant-time compare.

    Always runs a PBKDF2 pass even for an unknown user, so response time does not
    reveal whether the username exists.
    """
    credential = CREDENTIALS.get(username)
    # Compare against a dummy when the user is unknown, to equalize timing.
    salt_hex = credential.salt_hex if credential else "00" * 16
    expected = credential.hash_hex if credential else "ff" * 32
    computed = _hash(password or "", salt_hex)
    if credential is not None and hmac.compare_digest(computed, expected):
        return credential.role
    return None


@dataclass
class LockoutState:
    """Tracks failed attempts and a cooldown window, per session."""

    failed: int = 0
    locked_until: float = 0.0

    def seconds_remaining(self, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        return max(0, int(self.locked_until - now))

    def is_locked(self, now: Optional[float] = None) -> bool:
        return self.seconds_remaining(now) > 0

    def record_failure(self, now: Optional[float] = None) -> None:
        now = time.time() if now is None else now
        self.failed += 1
        if self.failed >= MAX_FAILED_ATTEMPTS:
            self.locked_until = now + LOCKOUT_SECONDS
            self.failed = 0

    def record_success(self) -> None:
        self.failed = 0
        self.locked_until = 0.0


def session_expired(last_active: Optional[float], now: Optional[float] = None) -> bool:
    """True when an authenticated session has been idle past the timeout."""
    if last_active is None:
        return False
    now = time.time() if now is None else now
    return (now - last_active) > SESSION_IDLE_TIMEOUT
