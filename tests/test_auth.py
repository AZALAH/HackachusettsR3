"""Tests for demo-grade authentication."""

from __future__ import annotations

from datamon.auth import (
    LOCKOUT_SECONDS,
    MAX_FAILED_ATTEMPTS,
    SESSION_IDLE_TIMEOUT,
    LockoutState,
    session_expired,
    verify_password,
)


def test_programmer_password_verifies():
    assert verify_password("programmer", "101010") == "programmer"


def test_judge_password_verifies():
    assert verify_password("judge", "Hello World!") == "judge"


def test_wrong_password_rejected():
    assert verify_password("programmer", "wrong") is None
    assert verify_password("judge", "hello world!") is None  # case-sensitive


def test_unknown_user_rejected():
    assert verify_password("intruder", "101010") is None
    assert verify_password("", "") is None


def test_lockout_after_max_failures():
    state = LockoutState()
    now = 1000.0
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert not state.is_locked(now)
        state.record_failure(now)
    assert state.is_locked(now)
    assert state.seconds_remaining(now) == LOCKOUT_SECONDS


def test_lockout_expires_after_cooldown():
    state = LockoutState()
    now = 1000.0
    for _ in range(MAX_FAILED_ATTEMPTS):
        state.record_failure(now)
    assert state.is_locked(now)
    assert not state.is_locked(now + LOCKOUT_SECONDS + 1)


def test_success_resets_failures():
    state = LockoutState()
    state.record_failure(1000.0)
    state.record_failure(1000.0)
    state.record_success()
    assert state.failed == 0
    assert not state.is_locked(1000.0)


def test_session_timeout():
    now = 5000.0
    assert not session_expired(now - 10, now)
    assert session_expired(now - SESSION_IDLE_TIMEOUT - 1, now)
    assert not session_expired(None, now)  # never-active session is not expired
