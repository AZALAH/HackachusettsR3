"""Tests for the post-login loader asset, fade, and login input hygiene."""

from __future__ import annotations

from datamon import intro
from datamon.auth import verify_password
from datamon.intro import FADE_CSS, LOADER_GIF, LOADING_SECONDS


def test_loader_gif_is_committed():
    # The animation ships as a pre-rendered asset so it plays reliably.
    assert LOADER_GIF.is_file()
    assert LOADER_GIF.stat().st_size > 1000  # a real GIF, not a stub


def test_loading_seconds_is_reasonable():
    assert 1 <= LOADING_SECONDS <= 30


def test_fade_css_present_and_reduced_motion_safe():
    assert "datamon-fade" in FADE_CSS
    assert "prefers-reduced-motion" in FADE_CSS


def test_render_helpers_exist():
    assert callable(intro.render_loading)
    assert callable(intro.render_fade)


def test_login_tolerates_surrounding_spaces_after_strip():
    assert verify_password("judge".strip(), " Hello World! ".strip()) == "judge"
    assert verify_password(" programmer ".strip(), " 101010 ".strip()) == "programmer"
